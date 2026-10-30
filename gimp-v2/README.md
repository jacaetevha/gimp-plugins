# GIMP 2.10 plug-ins

Plug-ins here are for GIMP 2.10. They won't load in GIMP 3; see [`../gimp-v3/`](../gimp-v3/) for those.

## Installing a plug-in

GIMP 2.10 plug-ins come in two kinds, and each goes in its own folder in your GIMP profile:

| Kind | File | Folder |
|------|------|--------|
| Python-Fu | `*.py` | `plug-ins` |
| Script-Fu | `*.scm` | `scripts` |

Where the profile lives:

| OS | Profile folder |
|----|----------------|
| macOS | `~/Library/Application Support/GIMP/2.10/` |
| Linux | `~/.config/GIMP/2.10/` (Flatpak: `~/.var/app/org.gimp.GIMP/config/GIMP/2.10/`) |
| Windows | `%APPDATA%\GIMP\2.10\` |

If you're unsure, **Edit → Preferences → Folders → Plug-ins** (or **Scripts**) lists the folders GIMP searches.

1. Copy the plug-in file into the right folder. A Python-Fu plug-in can sit directly in `plug-ins`; it doesn't need a subfolder.
2. On macOS and Linux, make a Python plug-in executable:
   ```sh
   chmod +x ~/Library/Application\ Support/GIMP/2.10/plug-ins/<plug-in>.py
   ```
3. Restart GIMP. (Script-Fu scripts can instead be reloaded with **Filters → Script-Fu → Refresh Scripts**.)

Python-Fu plug-ins need GIMP's Python 2 support. The official Windows and macOS builds include it; some Linux distributions dropped it, in which case use the Flatpak build.

## Plug-ins

None yet.
