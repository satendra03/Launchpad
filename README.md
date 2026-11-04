# Launchpad

A small Ubuntu/Linux desktop utility for adding manually installed applications to your app menu. Create launchers for apps that were installed outside the package manager—without editing `.desktop` files by hand.

## Features

- Create desktop launchers with an application name, executable, icon, description, category, and optional terminal launch.
- Pick files with the system GTK chooser when Zenity is installed; otherwise, the app uses Tk's built-in file dialog.
- Copy selected app icons into `~/.local/share/icons` so launchers do not depend on the icon remaining at its original path.
- Test-launch an executable before creating its launcher.
- Edit or remove launchers created by Launchpad.
- Optionally add Launchpad itself to the application menu. Its icon image is bundled in this repository as `applister.png`.

## Requirements

- Ubuntu or another Linux desktop environment
- Python 3
- Tkinter (`python3-tk` on Ubuntu/Debian)
- Zenity is optional, but recommended for a native GTK file chooser
- `update-desktop-database` is optional; the desktop menu usually refreshes without it

There are no Python packages to install with `pip`.

On Ubuntu/Debian, install the runtime components with:

```sh
sudo apt install python3-tk zenity desktop-file-utils
```

Zenity and `desktop-file-utils` are optional. If you only need the app, `python3-tk` is sufficient.

## Run

Clone or download this repository, then run `app.py` with Python 3:

```sh
python3 app.py
```

Keep `app.py` and `applister.png` together. The program loads its own window icon from the image beside the script.

## Add an application

1. Enter a name, or select an executable with **Browse**. Selecting an executable suggests a name and searches nearby files for an icon.
2. Select an icon if needed. The chosen icon is copied to `~/.local/share/icons` when you add the launcher.
3. Optionally enter a description, choose a category, and enable **Run in terminal** for command-line programs.
4. Use **Test run** to try launching the selected executable.
5. Click **Add to app list**. The launcher is written to `~/.local/share/applications` and should appear in your desktop's app search.

The executable must be a runnable Linux application or script. Some applications need a wrapper command or special arguments; this lightweight tool currently launches the selected executable directly.

## Manage launchers

The **Added Apps** list contains entries created by Launchpad. Select one to **Edit** its details or **Remove** its menu launcher. Removing a launcher does not delete the application executable or its icon.

Click **Add Launchpad to app list** to create a launcher for this utility. Keep the project files in their current location afterward, since that launcher points to `app.py` and its bundled icon there.

## Where files are stored

- Desktop launchers: `~/.local/share/applications/`
- Icons selected for added applications: `~/.local/share/icons/`
- Launchpad's bundled icon: `applister.png` beside `app.py`

## Limitations

- Launchpad creates standard Linux `.desktop` launchers; it does not install applications or resolve their dependencies.
- The **Test run** button may set the selected executable's executable permission bit if it is missing.
- Window-class detection is not included. Applications whose dock icons do not group with their launcher may require a manually adjusted `StartupWMClass` entry in their `.desktop` file.

## License

No license file is included yet. Add a `LICENSE` file before publishing if you want to grant others explicit permission to use, modify, and redistribute this project.
