#!/usr/bin/env python3
"""Downloads Sorter - tidy your personal folders from the terminal."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

try:
    from send2trash import send2trash
except ImportError:  # reported when trashing is needed
    send2trash = None

__version__ = "2.2.0"

console = Console()

HISTORY_FILE = Path.home() / ".downloads_sorter_history.json"
MAX_SHOWN = 30
MAX_DEPTH = 5

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
SKIPPED_EXTENSIONS = INCOMPLETE | {".lnk", ".url"}
SYSTEM_FILES = {"desktop.ini", "thumbs.db"}

# English and Dutch names of the personal folders. On Windows the real locations are
# also asked from the system (see windows_known_folders), which works in every language.
USER_FOLDER_NAMES = [
    "Downloads", "Desktop", "Documents", "Pictures", "Videos", "Music",
    "Bureaublad", "Documenten", "Afbeeldingen", "Video's", "Muziek",
]

# Windows "known folder" ids: Desktop, Documents, Downloads, Music, Pictures, Videos.
KNOWN_FOLDER_IDS = [
    "B4BFCC3A-DB2C-424C-B029-7FE99A87C641",
    "FDD39AD0-238F-46AF-ADB4-6C85480369C7",
    "374DE290-123F-4565-9164-39C4925E467B",
    "4BD8D571-6D19-48D3-BE97-422220080E43",
    "33E28130-4E1E-4676-835A-98395C3BC3BB",
    "18989B1D-99B5-455B-841C-AB7C74E4DDFC",
]

# Folders that are never scanned (lowercase names): tooling, system and game/app data.
SKIP_DIR_NAMES = {
    ".git", ".svn", ".idea", ".vscode", "node_modules", ".venv", "venv",
    "__pycache__", "appdata", "$recycle.bin", "system volume information",
    "my games", "saved games", "rockstar games", "electronic arts", "ubisoft",
    "steam", "epic games", "riot games", "windowspowershell", "powershell",
    "onenote notebooks", "custom office templates",
    "my music", "my pictures", "my videos",
    "mijn muziek", "mijn afbeeldingen", "mijn video's",
}

# A subfolder containing one of these files is a software project and is skipped completely.
PROJECT_MARKERS = {
    "package.json", "pom.xml", "build.gradle", "pyproject.toml", "requirements.txt",
    "cargo.toml", "go.mod", "composer.json", "manage.py",
}

PROTECTED_NAMES = {
    "windows", "program files", "program files (x86)", "programdata",
    "system32", "appdata", "$recycle.bin",
}
PROTECTED_PATHS = {
    Path(p) for p in ("/", "/usr", "/bin", "/sbin", "/etc", "/var", "/lib",
                      "/System", "/Library", "/Applications")
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    answer = console.input(f"[bold yellow]{question}[/bold yellow] [y/N] ")
    return answer.strip().lower() in {"y", "yes", "j", "ja"}


def make_progress(label: str) -> Progress:
    return Progress(
        TextColumn(f"[bold cyan]{label}[/bold cyan]"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[name]}[/dim]"),
        console=console,
    )


def is_protected(folder: Path) -> bool:
    """Never touch drive roots, the home folder itself or system folders."""
    resolved = folder.resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        return True
    if resolved in PROTECTED_PATHS:
        return True
    return any(part.lower() in PROTECTED_NAMES for part in resolved.parts)


def windows_known_folders() -> list[Path]:
    """Ask Windows where Desktop, Documents, Downloads, Music, Pictures and Videos really are."""
    if os.name != "nt":
        return []
    try:
        import ctypes

        get_path = ctypes.windll.shell32.SHGetKnownFolderPath
        get_path.restype = ctypes.c_long
        get_path.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        free = ctypes.windll.ole32.CoTaskMemFree
        free.argtypes = [ctypes.c_void_p]
    except (AttributeError, OSError):
        return []

    folders: list[Path] = []
    for guid in KNOWN_FOLDER_IDS:
        try:
            buffer = ctypes.c_wchar_p()
            result = get_path(UUID(guid).bytes_le, 0, None, ctypes.byref(buffer))
            if result == 0 and buffer.value:
                folders.append(Path(buffer.value))
            free(ctypes.cast(buffer, ctypes.c_void_p))
        except (OSError, ValueError):
            continue
    return folders


def user_folders() -> list[Path]:
    """Personal folders in any language, including OneDrive-redirected ones."""
    home = Path.home()
    home_real = home.resolve()
    candidates = windows_known_folders()
    bases = [home] + [p for p in sorted(home.glob("OneDrive*")) if p.is_dir()]
    for base in bases:
        candidates.extend(base / name for name in USER_FOLDER_NAMES)

    found: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        real = candidate.resolve()
        key = os.path.normcase(str(real))
        if real == home_real or key in seen:
            continue
        seen.add(key)
        found.append(candidate)
    return found


def is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    check = getattr(os.path, "isjunction", None)  # Python 3.12+
    return bool(check and check(path))


def is_cloud_placeholder(st: os.stat_result) -> bool:
    """OneDrive 'online only' files: hashing them would download them."""
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & 0x400000 or attrs & 0x40000)


def is_project_dir(path: Path) -> bool:
    """True for software projects (.git, package.json, pyproject.toml, ...)."""
    try:
        names = {entry.name.lower() for entry in path.iterdir()}
    except OSError:
        return False
    return ".git" in names or bool(names & PROJECT_MARKERS)


# --------------------------------------------------------------------------
# Sorting
# --------------------------------------------------------------------------

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


def sort_folders(root: Path, categories: dict[str, set[str]], depth: int):
    """Yield `root` and the subfolders (up to `depth` levels) that are safe to sort in place.

    Skips category folders (Images, Other, ...), hidden folders, game/system data,
    links and software projects.
    """
    yield root
    if depth <= 0:
        return
    skip = {name.lower() for name in categories} | {"other"}
    try:
        children = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return
    for child in children:
        name = child.name.lower()
        if (
            name in skip
            or name in SKIP_DIR_NAMES
            or name.startswith(".")
            or is_link_or_junction(child)
            or is_project_dir(child)
        ):
            continue
        yield from sort_folders(child, categories, depth - 1)


def plan_moves(
    folder: Path,
    categories: dict[str, set[str]],
    by_date: bool = False,
) -> list[tuple[Path, Path]]:
    """Return (source, destination) pairs for loose files in `folder` without touching anything."""
    moves: list[tuple[Path, Path]] = []
    for item in sorted(folder.iterdir()):
        if not item.is_file():
            continue
        if item.name.startswith("."):
            continue
        if item.name.lower() in SYSTEM_FILES:
            continue
        if item.suffix.lower() in SKIPPED_EXTENSIONS:
            continue
        target_dir = folder / category_for(item, categories)
        if by_date:
            try:
                stamp = datetime.fromtimestamp(item.stat().st_mtime)
            except OSError:
                continue
            target_dir = target_dir / f"{stamp:%Y}" / f"{stamp:%m}"
        moves.append((item, unique_destination(target_dir / item.name)))
    return moves


def execute(moves: list[tuple[Path, Path]]) -> list[dict[str, str]]:
    """Move the files with a progress bar. Returns the records that succeeded."""
    done: list[dict[str, str]] = []
    with make_progress("Sorting") as progress:
        task = progress.add_task("sort", total=len(moves), name="")
        for src, dest in moves:
            progress.update(task, name=escape(src.name[:40]))
            try:
                dest = unique_destination(dest)  # an earlier move may have taken this name
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
        parent = current.parent  # remove category/year/month folders that are empty now
        while parent != original.parent:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    HISTORY_FILE.unlink()
    return restored


# --------------------------------------------------------------------------
# Scanning, duplicates, old files, trash
# --------------------------------------------------------------------------

def walk_files(root: Path):
    """Yield every regular file below `root`.

    Skips hidden folders, system/game data, project folders (.git, package.json, ...),
    links and junctions.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here != root:
            is_project = ".git" in dirnames or ".git" in filenames or any(
                name.lower() in PROJECT_MARKERS for name in filenames
            )
            if is_project:
                dirnames[:] = []
                continue
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in SKIP_DIR_NAMES
            and not d.startswith(".")
            and not is_link_or_junction(here / d)
        ]
        for name in filenames:
            if name.startswith(".") or name.lower() in SYSTEM_FILES:
                continue
            path = here / name
            if path.suffix.lower() in SKIPPED_EXTENSIONS or path.is_symlink():
                continue
            yield path


def scan(folders: list[Path]) -> list[tuple[Path, os.stat_result]]:
    files: list[tuple[Path, os.stat_result]] = []
    seen: set[Path] = set()
    with console.status("[cyan]Scanning folders...[/cyan]"):
        for folder in folders:
            for path in walk_files(folder):
                if path in seen:
                    continue
                seen.add(path)
                try:
                    files.append((path, path.stat()))
                except OSError:
                    continue
    return files


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duplicates(files: list[tuple[Path, os.stat_result]]) -> list[list[tuple[Path, os.stat_result]]]:
    """Group identical files (same size, then same SHA-256). The first item of a group is the one to keep (oldest)."""
    by_size: dict[int, list[tuple[Path, os.stat_result]]] = defaultdict(list)
    for path, st in files:
        if st.st_size == 0 or is_cloud_placeholder(st):
            continue
        by_size[st.st_size].append((path, st))

    candidates = [group for group in by_size.values() if len(group) > 1]
    total = sum(len(group) for group in candidates)
    if total == 0:
        return []

    by_hash: dict[tuple[int, str], list[tuple[Path, os.stat_result]]] = defaultdict(list)
    with make_progress("Hashing") as progress:
        task = progress.add_task("hash", total=total, name="")
        for group in candidates:
            for path, st in group:
                progress.update(task, name=escape(path.name[:40]))
                try:
                    by_hash[(st.st_size, file_hash(path))].append((path, st))
                except OSError:
                    pass
                progress.advance(task)

    groups = [
        sorted(g, key=lambda x: (x[1].st_mtime, len(str(x[0])), str(x[0])))
        for g in by_hash.values()
        if len(g) > 1
    ]
    groups.sort(key=lambda g: g[0][1].st_size * (len(g) - 1), reverse=True)
    return groups


def find_old(
    files: list[tuple[Path, os.stat_result]],
    days: int,
    now: float | None = None,
) -> list[tuple[Path, os.stat_result]]:
    cutoff = (now if now is not None else time.time()) - days * 86400
    old = [(path, st) for path, st in files if st.st_mtime < cutoff]
    return sorted(old, key=lambda item: item[1].st_mtime)


def trash_paths(paths: list[Path]) -> int:
    """Send files to the trash / recycle bin (never a permanent delete)."""
    if send2trash is None:
        console.print("[bold red]send2trash is not installed.[/bold red] Run: pip install send2trash")
        return 0
    trashed = 0
    for path in paths:
        try:
            send2trash(str(path))
            trashed += 1
        except OSError as error:
            console.print(f"[red]✗[/red] {escape(path.name)}: {escape(str(error))}")
    return trashed


# --------------------------------------------------------------------------
# Actions (what the user asked for)
# --------------------------------------------------------------------------

def run_sort(
    folders: list[Path],
    categories: dict[str, set[str]],
    dry_run: bool,
    by_date: bool,
    depth: int,
    ask: bool,
    assume_yes: bool,
) -> None:
    moves: list[tuple[Path, Path]] = []
    for folder in folders:
        for target in sort_folders(folder, categories, depth):
            moves.extend(plan_moves(target, categories, by_date))

    if not moves:
        console.print("[bold green]✨ Already clean, nothing to do![/bold green]")
        return

    console.print(f"📂 {len(moves)} file(s) found in {len(folders)} folder(s)\n")

    if dry_run:
        for src, dest in moves[:200]:
            rel = dest.parent.relative_to(src.parent).as_posix()
            console.print(
                f"[dim]{escape(src.name)}[/dim] [cyan]→[/cyan] "
                f"[bold]{escape(src.parent.name)}/{escape(rel)}/[/bold]"
            )
        if len(moves) > 200:
            console.print(f"[dim]... and {len(moves) - 200} more file(s)[/dim]")
        console.print()
        print_summary(moves, categories, dry_run=True)
        return

    if ask and not confirm(f"Sort {len(moves)} file(s) in {len(folders)} folder(s)?", assume_yes):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    done = execute(moves)
    save_history(done)
    console.print()
    print_summary([(Path(r["from"]), Path(r["to"])) for r in done], categories, dry_run=False)
    console.print("[dim]Made a mistake? Run with --undo[/dim]")


def run_duplicates(folders: list[Path], dry_run: bool, assume_yes: bool) -> None:
    groups = find_duplicates(scan(folders))
    if not groups:
        console.print("[bold green]✨ No duplicates found.[/bold green]")
        return

    extras = [path for group in groups for path, _ in group[1:]]
    wasted = sum(group[0][1].st_size * (len(group) - 1) for group in groups)

    for group in groups[:MAX_SHOWN]:
        keep, keep_stat = group[0]
        console.print(f"[green]keep [/green] {escape(str(keep))} [dim]({human_size(keep_stat.st_size)})[/dim]")
        for path, _ in group[1:]:
            console.print(f"[red]trash[/red] {escape(str(path))}")
        console.print()
    if len(groups) > MAX_SHOWN:
        console.print(f"[dim]... and {len(groups) - MAX_SHOWN} more group(s)[/dim]\n")

    console.print(
        f"[bold]{len(extras)} duplicate file(s)[/bold] in {len(groups)} group(s), "
        f"[bold magenta]{human_size(wasted)}[/bold magenta] can be freed."
    )
    if dry_run:
        console.print("[yellow]Preview only, nothing was removed.[/yellow]")
        return
    if confirm(f"Move {len(extras)} duplicate(s) to the trash? The oldest copy is kept.", assume_yes):
        count = trash_paths(extras)
        console.print(f"[bold green]🗑  Moved {count} file(s) to the trash.[/bold green]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")


def run_old(folders: list[Path], days: int, dry_run: bool, assume_yes: bool) -> None:
    old = find_old(scan(folders), days)
    if not old:
        console.print(f"[bold green]✨ No files older than {days} day(s).[/bold green]")
        return

    table = Table(title=f"Files not modified for {days}+ days", border_style="cyan")
    table.add_column("Age", justify="right", style="magenta")
    table.add_column("Size", justify="right")
    table.add_column("Path", overflow="fold")
    now = time.time()
    for path, st in old[:MAX_SHOWN]:
        table.add_row(f"{int((now - st.st_mtime) / 86400)}d", human_size(st.st_size), escape(str(path)))
    console.print(table)
    if len(old) > MAX_SHOWN:
        console.print(f"[dim]... and {len(old) - MAX_SHOWN} more file(s)[/dim]")

    total = sum(st.st_size for _, st in old)
    console.print(f"\n[bold]{len(old)} file(s)[/bold], [bold magenta]{human_size(total)}[/bold magenta] in total.")
    if dry_run:
        console.print("[yellow]Preview only, nothing was removed.[/yellow]")
        return
    if confirm(f"Move {len(old)} old file(s) to the trash?", assume_yes):
        count = trash_paths([path for path, _ in old])
        console.print(f"[bold green]🗑  Moved {count} file(s) to the trash.[/bold green]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")


def run_top(folders: list[Path], count: int) -> None:
    biggest = sorted(scan(folders), key=lambda item: item[1].st_size, reverse=True)[:count]
    if not biggest:
        console.print("[yellow]No files found.[/yellow]")
        return
    table = Table(title=f"Top {len(biggest)} largest files", border_style="cyan")
    table.add_column("Size", justify="right", style="magenta")
    table.add_column("Modified", style="dim")
    table.add_column("Path", overflow="fold")
    for path, st in biggest:
        table.add_row(
            human_size(st.st_size),
            f"{datetime.fromtimestamp(st.st_mtime):%Y-%m-%d}",
            escape(str(path)),
        )
    console.print(table)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def print_banner() -> None:
    console.print(Text(BANNER, style="bold cyan"))
    console.print(
        Panel.fit(
            f"[bold]Downloads Sorter[/bold] v{__version__}  ·  keep your folders clean 🧹",
            border_style="cyan",
        )
    )


def print_summary(
    moves: list[tuple[Path, Path]],
    categories: dict[str, set[str]],
    dry_run: bool,
) -> None:
    counts = Counter(category_for(src, categories) for src, _ in moves)
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
        description="Sort and clean your personal folders (Downloads, Documents, Pictures, ...).",
    )
    parser.add_argument(
        "folders",
        nargs="*",
        help="folders to process (default: ~/Downloads)",
    )
    parser.add_argument(
        "-a", "--all", action="store_true",
        help="process all personal folders (Downloads, Desktop, Documents, Pictures, Videos, Music), in any language",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="only show what would happen")
    parser.add_argument("-u", "--undo", action="store_true", help="undo the last sorting run")
    parser.add_argument("-c", "--config", help="JSON file with custom categories")
    parser.add_argument("--by-date", action="store_true", help="sort into Category/YYYY/MM subfolders")
    parser.add_argument(
        "--depth", type=int, default=0, metavar="N",
        help=f"also sort subfolders up to N levels deep, each in place (max {MAX_DEPTH}, default 0)",
    )
    parser.add_argument("--duplicates", action="store_true", help="find duplicate files and trash the extra copies")
    parser.add_argument("--older-than", type=int, metavar="DAYS", help="trash files not modified for DAYS days")
    parser.add_argument("--top", type=int, metavar="N", help="show the N largest files")
    parser.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def resolve_folders(args: argparse.Namespace) -> list[Path] | None:
    if args.all:
        folders = user_folders()
        if not folders:
            console.print("[bold red]No personal folders found.[/bold red]")
            return None
    elif args.folders:
        folders = [Path(f).expanduser() for f in args.folders]
    else:
        folders = [Path.home() / "Downloads"]

    for folder in folders:
        if not folder.is_dir():
            console.print(f"[bold red]Folder not found:[/bold red] {escape(str(folder))}")
            return None
        if is_protected(folder):
            console.print(f"[bold red]Refusing to touch a protected folder:[/bold red] {escape(str(folder))}")
            return None
    return folders


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

    if not 0 <= args.depth <= MAX_DEPTH:
        console.print(f"[bold red]--depth must be between 0 and {MAX_DEPTH}.[/bold red]")
        return 1

    if args.older_than is not None:
        if args.all:
            console.print("[bold red]--older-than cannot be combined with --all.[/bold red] Pass a specific folder instead.")
            return 1
        if args.older_than < 1:
            console.print("[bold red]--older-than needs at least 1 day.[/bold red]")
            return 1

    folders = resolve_folders(args)
    if folders is None:
        return 1

    console.print("📂 Folders: " + ", ".join(escape(str(f)) for f in folders) + "\n")

    wants_action = args.duplicates or args.older_than is not None or args.top
    if args.by_date or args.depth or not wants_action:
        run_sort(
            folders,
            load_categories(args.config),
            dry_run=args.dry_run,
            by_date=args.by_date,
            depth=args.depth,
            ask=args.all or args.depth > 0,
            assume_yes=args.yes,
        )
    if args.duplicates:
        run_duplicates(folders, args.dry_run, args.yes)
    if args.older_than is not None:
        run_old(folders, args.older_than, args.dry_run, args.yes)
    if args.top:
        run_top(folders, args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())