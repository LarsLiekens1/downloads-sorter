# Downloads Sorter 🧹

A small CLI tool that sorts your Downloads folder into folders by file type,
with a colorful terminal UI.

```
 ____   ___  ____ _____ _____ ____
/ ___| / _ \|  _ \_   _| ____|  _ \
\___ \| | | | |_) || | |  _| | |_) |
 ___) | |_| |  _ <| | | |___|  _ <
|____/ \___/|_| \_\_| |_____|_| \_\
```

[![Tests](https://github.com/Larsliekens1/downloads-sorter/actions/workflows/tests.yml/badge.svg)](https://github.com/Larsliekens1/downloads-sorter/actions/workflows/tests.yml)

## Features

- Sorts files into `Images`, `Audio`, `Video`, `Documents`, `Code`, ... by extension
- Dry-run mode to preview before moving anything
- Never overwrites: duplicates become `file (1).png`
- Skips folders, hidden files, Windows system files (`desktop.ini`) and unfinished downloads (`.crdownload`, `.part`)
- Undo the last run with one command
- Custom categories via a JSON config
- One-click start scripts for Windows and Mac/Linux
- Works on Windows, macOS and Linux

## Quick start

Requirements: Python 3.10+ (on Windows tick "Add python.exe to PATH" during installation).

1. Download the repo (green **Code** button, then **Download ZIP**) and unzip it, or run:
   ```bash
   git clone https://github.com/Larsliekens1/downloads-sorter.git
   ```
2. Start it:
   - **Windows:** double-click `start.bat`
   - **Mac/Linux:** run `./start.sh` in a terminal

The first run sets up everything automatically (virtual environment and dependencies).
After that you get a menu: preview, sort or undo.

> Windows may show a blue SmartScreen warning for downloaded `.bat` files.
> Click **More info**, then **Run anyway**.

## Command line usage

Prefer the terminal? Set it up manually:

```bash
git clone https://github.com/Larsliekens1/downloads-sorter.git
cd downloads-sorter
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\activate
# Mac/Linux:            source .venv/bin/activate
pip install -r requirements.txt
```

Then run:

```bash
python downloads_sorter.py --dry-run     # preview only
python downloads_sorter.py               # sort ~/Downloads
python downloads_sorter.py ~/Desktop     # sort another folder
python downloads_sorter.py --undo        # undo the last run
python downloads_sorter.py -c config.json
python downloads_sorter.py --help
```

If PowerShell blocks the activation script, run this first (only affects the current window):

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

## Default categories

| Folder | Extensions |
| --- | --- |
| Images | png, jpg, jpeg, gif, webp, bmp, svg, heic |
| Audio | mp3, wav, flac, m4a, ogg, aac |
| Video | mp4, mkv, mov, avi, webm |
| Documents | pdf, doc, docx, txt, odt, rtf, md |
| Presentations | ppt, pptx, odp |
| Spreadsheets | xls, xlsx, csv, ods |
| Archives | zip, rar, 7z, tar, gz |
| Installers | exe, msi, dmg, pkg, deb, apk |
| Code | py, java, js, ts, json, html, css, sql, yml, yaml, sh |
| Other | everything else |

## Custom categories

Create a `config.json`:

```json
{
  "Images": [".png", ".jpg"],
  "Music": [".mp3", ".flac"],
  "School": [".pdf", ".docx"]
}
```

Run it with:

```bash
python downloads_sorter.py -c config.json
```

Files that match no category go to `Other`.

## Undo

Every run saves a history file (`~/.downloads_sorter_history.json`).
`--undo` moves the files of the last run back and removes the empty category folders.
Only the most recent run can be undone.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run automatically on every push through GitHub Actions (Ubuntu and Windows, Python 3.10 and 3.12).

## Project structure

```
downloads-sorter/
├── downloads_sorter.py
├── start.bat
├── start.sh
├── tests/
│   └── test_sorter.py
├── .github/workflows/tests.yml
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .gitattributes
├── .gitignore
├── LICENSE
└── README.md
```

## License

MIT