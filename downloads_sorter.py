#!/usr/bin/env python3
"""Downloads Sorter - tidy your Downloads folder from the terminal."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

__version__ = "1.0.1"

console = Console()

HISTORY_FILE = Path.home() / ".downloads_sorter_history.json"

BANNER = r"""
 ____   ___  ____ _____ _____ ____
/ ___| / _ \|  _ \_   _| ____|  _ \
\___ \| | | | |_) || | |  _| | |_) |
 ___) | |_| |  _ <| | | |___|  _ <
|____/ \___/|_| \_\_| |_____|_| \_\
"""

DEFAULT_CATEGORIES: dict[str, set[str]] = {
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".heic"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"},
    "Video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".md"},
    "Presentations": {".ppt", ".pptx", ".odp"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".apk"},
    "Code": {".py", ".java", ".js", ".ts", ".json", ".html", ".css", ".sql", ".yml", ".yaml", ".sh"},
}

ICONS = {
    "Images": "🖼️ ",
    "Audio": "🎵",
    "Video": "🎬",
    "Documents": "📄",
    "Presentations": "📊",
    "Spreadsheets": "📈",
    "Archives": "🗜️ ",
    "Installers": "💿",
    "Code": "💻",
    "Other": "📦",
}

INCOMPLETE = {".crdownload", ".part", ".tmp", ".download"}

SYSTEM_FILES = {"desktop.ini", "thumbs.db"}


def load_categories(config_path: str | None) -> dict[str, set[str]]:
    """Load custom categories from a JSON file, or use the defaults."""
    if not config_path:
        return DEFAULT_CATEGORIES
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return {
        name: {e.lower() if e.startswith(".") else f".{e.lower()}" for e in exts}
        for name, exts in data.items()
    }


def category_for(path: Path, categories: dict[str, set[str]]) -> str:
    ext = path.suffix.lower()
    for name, extensions in categories.items():
        if ext in extensions:
            return name
    return "Other"


def unique_destination(dest: Path) -> Path:
    """Never overwrite: 'file.png' becomes 'file (1).png', 'file (2).png', ..."""
    if not dest.exists():
        return dest
    counter = 1
    while True:
        candidate = dest.with_name(f"{dest.stem} ({counter}){dest.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def plan_moves(folder: Path, categories: dict[str, set[str]]) -> list[tuple[Path, Path]]:
    """Return a list of (source, destination) pairs without touching any file."""
    moves: list[tuple[Path, Path]] = []
    for item in sorted(folder.iterdir()):
        if not item.is_file():
            continue
        if item.name.startswith("."):
            continue
        if item.name.lower() in SYSTEM_FILES:
            continue
        if item.suffix.lower() in INCOMPLETE:
            continue
        target_dir = folder / category_for(item, categories)
        moves.append((item, unique_destination(target_dir / item.name)))
    return moves


def execute(moves: list[tuple[Path, Path]]) -> list[dict[str, str]]:
    """Move the files with a progress bar. Returns the records that succeeded."""
    done: list[dict[str, str]] = []
    progress = Progress(
        TextColumn("[bold cyan]Sorting[/bold cyan]"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[name]}[/dim]"),
        console=console,
    )
    with progress:
        task = progress.add_task("sort", total=len(moves), name="")
        for src, dest in moves:
            progress.update(task, name=escape(src.name[:40]))
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                done.append({"from": str(src), "to": str(dest)})
            except OSError as error:
                console.print(f"[red]✗[/red] {escape(src.name)}: {escape(str(error))}")
            progress.advance(task)
    return done


def save_history(records: list[dict[str, str]]) -> None:
    HISTORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def undo() -> int:
    """Move every file of the last run back to where it came from."""
    if not HISTORY_FILE.exists():
        return 0
    records = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    restored = 0
    for record in reversed(records):
        current = Path(record["to"])
        original = Path(record["from"])
        if not current.exists():
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current), str(unique_destination(original)))
        restored += 1
        try:
            current.parent.rmdir()  # remove the category folder if it is empty now
        except OSError:
            pass
    HISTORY_FILE.unlink()
    return restored


def print_banner() -> None:
    console.print(Text(BANNER, style="bold cyan"))
    console.print(
        Panel.fit(
            f"[bold]Downloads Sorter[/bold] v{__version__}  ·  keep your folder clean 🧹",
            border_style="cyan",
        )
    )


def print_summary(moves: list[tuple[Path, Path]], dry_run: bool) -> None:
    counts = Counter(dest.parent.name for _, dest in moves)
    table = Table(
        title="Preview (nothing moved)" if dry_run else "Done!",
        title_style="bold yellow" if dry_run else "bold green",
        border_style="cyan",
    )
    table.add_column("Folder", style="bold")
    table.add_column("Files", justify="right", style="magenta")
    for name, count in counts.most_common():
        table.add_row(f"{ICONS.get(name, '📁')} {name}", str(count))
    table.add_section()
    table.add_row("Total", str(sum(counts.values())), style="bold green")
    console.print(table)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="downloads-sorter",
        description="Sort your Downloads folder into folders by file type.",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="folder to sort (default: ~/Downloads)",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="only show what would happen")
    parser.add_argument("-u", "--undo", action="store_true", help="undo the last sorting run")
    parser.add_argument("-c", "--config", help="JSON file with custom categories")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print_banner()

    if args.undo:
        restored = undo()
        if restored:
            console.print(f"[bold green]↩ Restored {restored} file(s).[/bold green]")
        else:
            console.print("[yellow]Nothing to undo.[/yellow]")
        return 0

    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        console.print(f"[bold red]Folder not found:[/bold red] {escape(str(folder))}")
        return 1

    categories = load_categories(args.config)
    moves = plan_moves(folder, categories)

    if not moves:
        console.print("[bold green]✨ Already clean, nothing to do![/bold green]")
        return 0

    console.print(f"📂 Scanning [bold]{escape(str(folder))}[/bold]: {len(moves)} file(s) found\n")

    if args.dry_run:
        for src, dest in moves:
            console.print(
                f"[dim]{escape(src.name)}[/dim] [cyan]→[/cyan] "
                f"[bold]{escape(dest.parent.name)}/[/bold]"
            )
        console.print()
        print_summary(moves, dry_run=True)
        return 0

    done = execute(moves)
    save_history(done)
    console.print()
    print_summary(
        [(Path(r["from"]), Path(r["to"])) for r in done],
        dry_run=False,
    )
    console.print("[dim]Made a mistake? Run with --undo[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())