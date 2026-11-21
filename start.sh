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

if [ ! -f ".venv/.deps_v2" ]; then
    echo "Installing dependencies..."
    .venv/bin/python -m pip install -q -r requirements.txt
    touch .venv/.deps_v2
fi

RUN=".venv/bin/python downloads_sorter.py"

while true; do
    clear
    echo "=============================="
    echo "       DOWNLOADS SORTER"
    echo "=============================="
    echo
    echo "  Downloads folder"
    echo "  [1] Preview sort"
    echo "  [2] Sort"
    echo "  [3] Undo the last sort"
    echo "  [4] Trash files older than 30 days"
    echo
    echo "  All personal folders (Downloads, Desktop, Documents, Pictures, Videos, Music)"
    echo "  [5] Preview sort"
    echo "  [6] Sort"
    echo "  [7] Find duplicates (preview)"
    echo "  [8] Remove duplicates"
    echo "  [9] Show the 20 largest files"
    echo
    echo "  [0] Quit"
    echo
    read -r -p "Choose 0-9: " choice
    case "$choice" in
        1) $RUN --dry-run ;;
        2) $RUN ;;
        3) $RUN --undo ;;
        4) $RUN --older-than 30 ;;
        5) $RUN --all --dry-run ;;
        6) $RUN --all ;;
        7) $RUN --all --duplicates --dry-run ;;
        8) $RUN --all --duplicates ;;
        9) $RUN --all --top 20 ;;
        0) exit 0 ;;
        *) continue ;;
    esac
    echo
    read -r -p "Press Enter to continue..."
done