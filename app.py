#!/usr/bin/env python3
"""Launchpad (lite) - add manually installed apps to the Ubuntu app list.
Only needs: python3-tk (no pip packages). Uses Zenity for native file dialogs when available."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.expanduser("~/.local/share/applications")
ICON_DIR = os.path.expanduser("~/.local/share/icons")
SELF_ICON = os.path.join(APP_DIR, "icon.png")
SELF_CLASS = "Launchpad"
MARKER = "X-Launchpad=true"
CATEGORIES = ["Utility", "Development", "Network", "Office", "Graphics",
              "AudioVideo", "Game", "Education", "System", "Settings"]

BG, CARD, FIELD, BORDER = "#15151c", "#1d1d27", "#262633", "#33334a"
TEXT, MUTED, FIRE, FIRE_H = "#f2f2f7", "#8b8b9e", "#ff5a1f", "#ff7a3d"


# ---------------- helpers ----------------
def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "app"


def refresh_db():
    try:
        subprocess.run(["update-desktop-database", APPS_DIR], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def choose_file(title, filetypes=None):
    """Open the desktop's GTK file chooser when available, else use Tk's chooser."""
    zenity = shutil.which("zenity")
    if zenity:
        # GTK/Zenity remembers its last folder outside this app. An explicit
        # starting directory avoids stale paths from older project locations.
        home = os.path.expanduser("~")
        command = [zenity, "--file-selection", f"--title={title}", "--modal",
                   f"--filename={home}{os.sep}"]
        for label, patterns in filetypes or ():
            command.append(f"--file-filter={label} | {' '.join(patterns)}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
        except OSError:
            pass
        else:
            return result.stdout.strip() if result.returncode == 0 else ""
    options = {"title": title, "initialdir": os.path.expanduser("~")}
    if filetypes:
        options["filetypes"] = filetypes
    return filedialog.askopenfilename(**options)


def read_key(content, key):
    m = re.search(rf"^{key}=(.*)$", content, re.M)
    return m.group(1).strip() if m else ""


def parse_exec(line):
    """Return the executable path from a desktop-entry Exec value.

    Launchpad deliberately does not preserve or add --no-sandbox.
    """
    import shlex
    try:
        parts = shlex.split(line)
    except ValueError:
        return ""
    return parts[0] if parts else ""


# ---------------- app ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__(className=SELF_CLASS)  # window class used to match the launcher
        self.title("Launchpad")
        self.geometry("560x800")
        self.configure(bg=BG)
        self.resizable(False, True)

        # give Launchpad its own window/dock icon
        try:
            self._icon_img = tk.PhotoImage(file=SELF_ICON)
            self.iconphoto(True, self._icon_img)
        except Exception:
            pass

        self.vars = {k: tk.StringVar() for k in ("name", "exec", "icon", "comment")}
        self.category = tk.StringVar(value="Utility")
        self.terminal = tk.BooleanVar()
        self.style_widgets()
        self.build()
        self.reload_list()

    def style_widgets(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, arrowcolor=TEXT,
                    padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", FIRE)

    # ---- small widget helpers ----
    def label(self, parent, text, **kw):
        bg = kw.pop("bg", parent["bg"])
        return tk.Label(parent, text=text, bg=bg, fg=kw.pop("fg", MUTED),
                        font=kw.pop("font", ("Ubuntu", 9)), **kw)

    def entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                        relief="flat", font=("Ubuntu", 11), highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=FIRE)

    def button(self, parent, text, cmd, primary=False, **kw):
        bg, hv = (FIRE, FIRE_H) if primary else (FIELD, BORDER)
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white" if primary else TEXT,
                      activebackground=hv, activeforeground="white", relief="flat",
                      bd=0, cursor="hand2", font=("Ubuntu", 10, "bold" if primary else "normal"), **kw)
        b.bind("<Enter>", lambda e: b.configure(bg=hv))
        b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    def check(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=CARD, fg=TEXT,
                              selectcolor=FIELD, activebackground=CARD, activeforeground=TEXT,
                              highlightthickness=0, bd=0, font=("Ubuntu", 10))

    # ---- layout ----
    def build(self):
        tk.Label(self, text="Launchpad", bg=BG, fg=FIRE,
                 font=("Ubuntu", 20, "bold")).pack(anchor="w", padx=24, pady=(16, 0))
        self.label(self, "Add manually installed apps to your app list", bg=BG
                   ).pack(anchor="w", padx=24, pady=(0, 10))

        card = tk.Frame(self, bg=CARD)
        card.pack(fill="x", padx=24)
        card.columnconfigure(0, weight=1)

        rows = [("NAME", "name", None),
                ("EXECUTABLE", "exec", self.pick_exec),
                ("ICON (png / svg)", "icon", self.pick_icon),
            ("DESCRIPTION", "comment", None)]
        r = 0
        for text, key, browse in rows:
            btn_text, btn_cmd = ("Browse", browse) if callable(browse) else (browse or (None, None))
            self.label(card, text).grid(row=r, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 2))
            e = self.entry(card, self.vars[key])
            e.grid(row=r + 1, column=0, columnspan=1 if btn_cmd else 2, sticky="ew",
                   padx=(16, 8 if btn_cmd else 16), ipady=6)
            if btn_cmd:
                self.button(card, btn_text, btn_cmd, width=8).grid(
                    row=r + 1, column=1, padx=(0, 16), ipady=3)
            r += 2

        self.label(card, "CATEGORY").grid(row=r, column=0, sticky="w", padx=16, pady=(10, 2))
        ttk.Combobox(card, textvariable=self.category, values=CATEGORIES, state="readonly"
                     ).grid(row=r + 1, column=0, columnspan=2, sticky="ew", padx=16)
        self.check(card, "Run in terminal", self.terminal).grid(
            row=r + 2, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 0))
        
        btns = tk.Frame(card, bg=CARD)
        btns.grid(row=r + 3, column=0, columnspan=2, sticky="ew", padx=16, pady=14)
        btns.columnconfigure(1, weight=1)
        self.button(btns, "Test run", self.test_run).grid(row=0, column=0, sticky="ew", ipady=8, ipadx=14)
        self.button(btns, "Add to app list", self.create_entry, primary=True).grid(
            row=0, column=1, sticky="ew", padx=(8, 0), ipady=8)

        self.label(self, "ADDED APPS", bg=BG).pack(anchor="w", padx=24, pady=(12, 4))
        box = tk.Frame(self, bg=CARD)
        box.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        self.listbox = tk.Listbox(box, bg=CARD, fg=TEXT, selectbackground=FIRE,
                                  selectforeground="white", relief="flat", highlightthickness=0,
                                  font=("Ubuntu", 11), activestyle="none", height=4)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=10)

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=24, pady=(0, 14))
        self.button(bar, "Add Launchpad to app list", self.install_self).pack(side="left", ipadx=8, ipady=3)
        self.button(bar, "Remove", self.remove_entry).pack(side="right", ipadx=10, ipady=3)
        self.button(bar, "Edit", self.edit_entry).pack(side="right", padx=(0, 8), ipadx=10, ipady=3)

    # ---- pickers ----
    def pick_exec(self):
        p = choose_file("Select the executable")
        if not p:
            return
        self.vars["exec"].set(p)
        if not self.vars["name"].get():
            self.vars["name"].set(os.path.basename(p).replace("-", " ").replace("_", " ").title())
        if not self.vars["icon"].get():
            self.guess_icon(os.path.dirname(p))

    def pick_icon(self):
        p = choose_file("Select the icon", filetypes=[
            ("Images", ("*.png", "*.svg", "*.xpm", "*.ico", "*.jpg")),
            ("All files", ("*",))])
        if p:
            self.vars["icon"].set(p)

    def guess_icon(self, folder):
        for root, _, files in os.walk(folder):
            if root[len(folder):].count(os.sep) > 2:
                continue
            for f in files:
                if f.lower().endswith((".png", ".svg")) and ("icon" in f.lower() or "logo" in f.lower()):
                    self.vars["icon"].set(os.path.join(root, f))
                    return

    # ---- test run ----
    def test_run(self):
        exe = self.vars["exec"].get().strip()
        if not exe or not os.path.isfile(exe):
            return messagebox.showerror("Missing info", "Pick a valid executable first.")
        try:
            os.chmod(exe, os.stat(exe).st_mode | 0o111)
        except OSError:
            pass
        cmd = [exe]
        if self.terminal.get():
            term = shutil.which("gnome-terminal") or shutil.which("x-terminal-emulator")
            if term:
                cmd = [term, "--"] + cmd
        log = tempfile.NamedTemporaryFile(prefix="applister-", suffix=".log", delete=False)
        try:
            proc = subprocess.Popen(cmd, cwd=os.path.dirname(exe), stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as e:
            return messagebox.showerror("Could not start", f"{e}\n\nIs this the right file? "
                                        "(scripts need a #! line, .jar needs java -jar, etc.)")

        def check():
            code = proc.poll()
            if code is None:
                messagebox.showinfo("Test run", "The app is still running after 4 seconds - looks good.")
            else:
                try:
                    out = open(log.name, errors="replace").read()[-1500:].strip()
                except OSError:
                    out = ""
                messagebox.showerror("App exited early",
                                     f"Exit code: {code}\n\n{out or '(no output)'}")
        self.after(4000, check)

    # ---- create / edit / remove ----
    def create_entry(self):
        name, exe = self.vars["name"].get().strip(), self.vars["exec"].get().strip()
        if not name or not exe:
            return messagebox.showerror("Missing info", "Name and Executable are required.")
        if not os.path.isfile(exe):
            return messagebox.showerror("Not found", f"File does not exist:\n{exe}")
        try:
            os.chmod(exe, os.stat(exe).st_mode | 0o111)
        except OSError:
            pass

        icon = self.vars["icon"].get().strip()
        if icon and os.path.isfile(icon):
            ext = os.path.splitext(icon)[1]
            installed_icon = os.path.join(ICON_DIR, f"{slugify(name)}{ext}")
            try:
                os.makedirs(ICON_DIR, exist_ok=True)
                if os.path.realpath(icon) != os.path.realpath(installed_icon):
                    shutil.copy2(icon, installed_icon)
            except OSError as e:
                return messagebox.showerror("Icon copy failed", str(e))
            icon = installed_icon
        exec_line = f'"{exe}" %U'
        lines = ["[Desktop Entry]", "Type=Application", f"Name={name}",
                 f"Comment={self.vars['comment'].get().strip() or name}",
                 f"Exec={exec_line}", f"Path={os.path.dirname(exe)}",
                 f"Terminal={'true' if self.terminal.get() else 'false'}",
                 f"Categories={self.category.get()};", "StartupNotify=true", MARKER]
        if icon:
            lines.insert(5, f"Icon={icon}")
        os.makedirs(APPS_DIR, exist_ok=True)
        target = os.path.join(APPS_DIR, f"{slugify(name)}.desktop")
        with open(target, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(target, 0o755)
        refresh_db()
        messagebox.showinfo("Done", f"'{name}' added. Search for it in your app list.")
        for v in self.vars.values():
            v.set("")
        self.terminal.set(False)
        self.reload_list()

    def reload_list(self):
        self.listbox.delete(0, "end")
        self.entries = []
        if not os.path.isdir(APPS_DIR):
            return
        for fn in sorted(os.listdir(APPS_DIR)):
            path = os.path.join(APPS_DIR, fn)
            if not fn.endswith(".desktop"):
                continue
            try:
                content = open(path).read()
            except OSError:
                continue
            if MARKER in content:
                self.listbox.insert("end", "  " + (read_key(content, "Name") or fn))
                self.entries.append(path)

    def edit_entry(self):
        sel = self.listbox.curselection()
        if not sel:
            return messagebox.showinfo("Edit", "Select an app in the list first.")
        content = open(self.entries[sel[0]]).read()
        exe = parse_exec(read_key(content, "Exec"))
        self.vars["name"].set(read_key(content, "Name"))
        self.vars["exec"].set(exe)
        self.vars["icon"].set(read_key(content, "Icon"))
        self.vars["comment"].set(read_key(content, "Comment"))
        self.terminal.set(read_key(content, "Terminal") == "true")
        cat = read_key(content, "Categories").rstrip(";").split(";")[0]
        if cat in CATEGORIES:
            self.category.set(cat)

    def remove_entry(self):
        sel = self.listbox.curselection()
        if sel and messagebox.askyesno("Remove", "Remove this entry from the app list?\n(App files are NOT deleted.)"):
            os.remove(self.entries[sel[0]])
            refresh_db()
            self.reload_list()

    def install_self(self):
        script = os.path.abspath(__file__)
        try:
            os.makedirs(APPS_DIR, exist_ok=True)
            target = os.path.join(APPS_DIR, "launchpad.desktop")
            lines = ["[Desktop Entry]", "Type=Application", "Name=Launchpad",
                     "Comment=Add manually installed apps to the app list",
                     f'Exec="{sys.executable}" "{script}"', f"Path={os.path.dirname(script)}",
                     f"Icon={SELF_ICON}", "Terminal=false", "Categories=Utility;",
                     f"StartupWMClass={SELF_CLASS}", MARKER]
            with open(target, "w") as f:
                f.write("\n".join(lines) + "\n")
            os.chmod(target, 0o755)
            refresh_db()
        except OSError as e:
            return messagebox.showerror("Failed", str(e))
        messagebox.showinfo("Done", "Launchpad is now in your app list.\n"
                            "Keep this script where it is, or re-run this if you move it.")
        self.reload_list()


if __name__ == "__main__":
    App().mainloop()
