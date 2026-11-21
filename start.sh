#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python was not found. Install Python 3.10+ first."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    $PY -m venv .venv
fi

if [ ! -f ".venv/.deps_ok" ]; then
    echo "Installing dependencies..."
    .venv/bin/python -m pip install -q -r requirements.txt
    touch .venv/.deps_ok
fi

while true; do
    clear
    echo "=============================="
    echo "       DOWNLOADS SORTER"
    echo "=============================="
    echo
    echo "  [1] Preview (nothing is moved)"
    echo "  [2] Sort my Downloads folder"
    echo "  [3] Undo the last sort"
    echo "  [4] Quit"
    echo
    read -r -p "Choose 1-4: " choice
    case "$choice" in
        1) .venv/bin/python downloads_sorter.py --dry-run ;;
        2) .venv/bin/python downloads_sorter.py ;;
        3) .venv/bin/python downloads_sorter.py --undo ;;
        4) exit 0 ;;
        *) continue ;;
    esac
    echo
    read -r -p "Press Enter to continue..."
done