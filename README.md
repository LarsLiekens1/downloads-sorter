# Downloads Sorter 🧹

A small CLI tool that sorts and cleans your personal folders (Downloads, Desktop,
Documents, Pictures, Videos, Music) from the terminal, with a colorful UI.

```
 ____   ___  ____ _____ _____ ____
/ ___| / _ \|  _ \_   _| ____|  _ \
\___ \| | | | |_) || | |  _| | |_) |
 ___) | |_| |  _ <| | | |___|  _ <
|____/ \___/|_| \_\_| |_____|_| \_\
```

[![Tests](https://github.com/Larsliekens1/downloads-sorter/actions/workflows/tests.yml/badge.svg)](https://github.com/Larsliekens1/downloads-sorter/actions/workflows/tests.yml)

## Features

- Sorts loose files into `Images`, `Audio`, `Video`, `Documents`, `Code`, ... by extension
- `--all`: works on all your personal folders at once
- `--by-date`: sorts into `Category/YYYY/MM` subfolders
- `--duplicates`: finds identical files (size, then SHA-256) and trashes the extra copies
- `--older-than DAYS`: trashes files you have not touched for a long time
- `--top N`: shows the largest files
- Dry-run mode to preview before changing anything
- Undo the last sort with one command
- Never overwrites: duplicates become `file (1).png`
- Deletes only to the trash, always with confirmation
- Custom categories via a JSON config
- One-click start scripts for Windows and Mac/Linux
- `--depth N`: also sorts subfolders up to N levels deep, each folder in place

## Safety

- Refuses drive roots, your home folder itself and system folders (Windows, Program Files, AppData, ...)
- Only sorts loose files at the top of a folder, existing subfolders stay untouched
- Skips hidden folders, shortcuts (`.lnk`) and `desktop.ini`
- Skips software projects (folders with `.git`, `package.json`, `pyproject.toml`, ...), virtual environments and game data such as `My Games`
- Never downloads OneDrive "online only" files when looking for duplicates
- `--older-than` cannot be combined with `--all`

Always run with `--dry-run` first.

## Quick start

Requirements: Python 3.10+ (on Windows tick "Add python.exe to PATH" during installation).

1. Download the repo (green **Code** button, then **Download ZIP**) and unzip it, or run:
   ```bash
   git clone https://github.com/Larsliekens1/downloads-sorter.git
   ```
2. Start it:
   - **Windows:** double-click `start.bat`
   - **Mac/Linux:** run `./start.sh` in a terminal

The first run sets up everything automatically. After that you get a menu with
preview, sort, undo, duplicates, old files and largest files.

> Windows may show a blue SmartScreen warning for downloaded `.bat` files.
> Click **More info**, then **Run anyway**.

## Command line usage


```bash
git clone https://github.com/Larsliekens1/downloads-sorter.git
cd downloads-sorter
python -m venv .venv
# Windows (PowerShell): .venv\Scripts\activate
# Mac/Linux:            source .venv/bin/activate
pip install -r requirements.txt
```

```bash
python downloads_sorter.py --dry-run                 # preview sorting ~/Downloads
python downloads_sorter.py                           # sort ~/Downloads
python downloads_sorter.py --all --dry-run           # preview all personal folders
python downloads_sorter.py --all --by-date           # sort into Category/YYYY/MM
python downloads_sorter.py --all --duplicates        # find and trash duplicates
python downloads_sorter.py --older-than 30           # trash old files in Downloads
python downloads_sorter.py --all --top 20            # 20 largest files
python downloads_sorter.py ~/Desktop ~/Pictures      # specific folders
python downloads_sorter.py --undo                    # undo the last sort
python downloads_sorter.py --help
python downloads_sorter.py --all --depth 1 --dry-run   # also sort one level of subfolders
```

If PowerShell blocks the activation script, run this first (only affects the current window):

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

### Install as a real command

```bash
pip install -e .
downloads-sorter --all --dry-run
```

## Options

| Option | Description |
| --- | --- |
| `folders` | Folders to process (default: `~/Downloads`) |
| `-a`, `--all` | Downloads, Desktop, Documents, Pictures, Videos, Music (+ OneDrive versions) |
| `-n`, `--dry-run` | Only show what would happen |
| `-u`, `--undo` | Undo the last sorting run |
| `--by-date` | Sort into `Category/YYYY/MM` |
| `--duplicates` | Find duplicates, trash extra copies (oldest is kept) |
| `--older-than DAYS` | Trash files not modified for DAYS days |
| `--top N` | Show the N largest files |
| `-c`, `--config` | JSON file with custom categories |
| `-y`, `--yes` | Do not ask for confirmation |

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

`config.json`:

```json
{
  "Images": [".png", ".jpg"],
  "Music": [".mp3", ".flac"],
  "School": [".pdf", ".docx"]
}
```

```bash
python downloads_sorter.py -c config.json
```

## Undo

Every sort saves a history file (`~/.downloads_sorter_history.json`).
`--undo` moves the files of the last sort back and removes the empty folders it created.
Only the most recent sort can be undone. Files sent to the trash can be restored from the Recycle Bin / Trash.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run on every push through GitHub Actions (Ubuntu and Windows, Python 3.10 and 3.12).

## Project structure

```
downloads-sorter/
├── downloads_sorter.py
├── start.bat
├── start.sh
├── pyproject.toml
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