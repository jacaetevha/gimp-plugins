# GIMP 3 plug-ins

Plug-ins here are for GIMP 3.x. They won't load in GIMP 2.10; see [`../gimp-v2/`](../gimp-v2/) for those.

## Installing a plug-in

GIMP 3 only loads a plug-in that sits in **its own folder, named the same as the plug-in file** (without the extension), inside your profile's `plug-ins` folder:

```
plug-ins/
└── page-rip/
    └── page-rip.py
```

Each plug-in in this directory is already laid out that way, so you install the whole folder.

Where the `plug-ins` folder lives:

| OS | Folder |
|----|--------|
| macOS | `~/Library/Application Support/GIMP/3.0/plug-ins/` |
| Linux | `~/.config/GIMP/3.0/plug-ins/` (Flatpak: `~/.var/app/org.gimp.GIMP/config/GIMP/3.0/plug-ins/`) |
| Windows | `%APPDATA%\GIMP\3.0\plug-ins\` |

If you're unsure, **Edit → Preferences → Folders → Plug-ins** lists the folders GIMP searches.

1. Copy the plug-in's folder into `plug-ins`, or symlink it so pulling this repo updates the plug-in:
   ```sh
   ln -s "$PWD/page-rip" ~/Library/Application\ Support/GIMP/3.0/plug-ins/page-rip
   ```
   On Windows, copy the folder.
2. On macOS and Linux, make sure the script is executable (it is in this repo, but copying can lose it):
   ```sh
   chmod +x ~/Library/Application\ Support/GIMP/3.0/plug-ins/page-rip/page-rip.py
   ```
3. Restart GIMP.

GIMP 3 ships with its own Python 3, so there's nothing else to install.

If a plug-in doesn't appear in its menu, start GIMP from a terminal with `--verbose` to see whether it was found and why it failed to load.

## Plug-ins

| Plug-in | Menu | What it does |
|---------|------|--------------|
| [Page Rip](page-rip/) | Filters → Decor → Page Rip… | Cuts a band out of an image and joins the rest with a torn-paper edge |
