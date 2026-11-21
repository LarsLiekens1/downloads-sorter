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

## Features

- Sorts files into `Images`, `Audio`, `Video`, `Documents`, `Code`, ... by extension
- Dry-run mode to preview before moving anything
- Never overwrites: duplicates become `file (1).png`
- Skips folders, hidden files and unfinished downloads (`.crdownload`, `.part`)
- Undo the last run with one command
- Custom categories via a JSON config
- Works on Windows, macOS and Linux

## Install

```bash
git clone https://github.com/LarsLiekens1/downloads-sorter.git
cd downloads-sorter
pip install -r requirements.txt
```

## Usage

```bash
python downloads_sorter.py --dry-run     # preview only
python downloads_sorter.py               # sort ~/Downloads
python downloads_sorter.py ~/Desktop     # sort another folder
python downloads_sorter.py --undo        # undo the last run
python downloads_sorter.py -c config.json
```

## Custom categories

`config.json`:

```json
{
  "Images": [".png", ".jpg"],
  "Music": [".mp3", ".flac"],
  "School": [".pdf", ".docx"]
}
```

Files that match no category go to `Other`.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT