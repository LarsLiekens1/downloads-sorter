import os
import time
from datetime import datetime
from pathlib import Path

import pytest

import downloads_sorter as ds


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "HISTORY_FILE", tmp_path / "history.json")


def make(path: Path, content: str = "x", age_days: float = 0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if age_days:
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
    return path


def test_category_for_known_and_unknown():
    cats = ds.DEFAULT_CATEGORIES
    assert ds.category_for(Path("photo.PNG"), cats) == "Images"
    assert ds.category_for(Path("song.mp3"), cats) == "Audio"
    assert ds.category_for(Path("weird.xyz"), cats) == "Other"


def test_unique_destination_adds_counter(tmp_path):
    make(tmp_path / "a.png")
    assert ds.unique_destination(tmp_path / "a.png") == tmp_path / "a (1).png"
    make(tmp_path / "a (1).png")
    assert ds.unique_destination(tmp_path / "a.png") == tmp_path / "a (2).png"


def test_plan_skips_folders_hidden_and_incomplete(tmp_path):
    make(tmp_path / "keep.png")
    make(tmp_path / ".hidden.png")
    make(tmp_path / "busy.crdownload")
    (tmp_path / "somefolder").mkdir()
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES)
    assert [src.name for src, _ in moves] == ["keep.png"]


def test_plan_skips_system_files_and_shortcuts(tmp_path):
    make(tmp_path / "desktop.ini")
    make(tmp_path / "Thumbs.db")
    make(tmp_path / "game.lnk")
    make(tmp_path / "song.mp3")
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES)
    assert [src.name for src, _ in moves] == ["song.mp3"]


def test_execute_and_undo_roundtrip(tmp_path):
    make(tmp_path / "a.png", "img")
    make(tmp_path / "b.mp3", "song")
    done = ds.execute(ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES))
    ds.save_history(done)

    assert (tmp_path / "Images" / "a.png").exists()
    assert (tmp_path / "Audio" / "b.mp3").exists()

    assert ds.undo() == 2
    assert (tmp_path / "a.png").exists()
    assert (tmp_path / "b.mp3").exists()
    assert not (tmp_path / "Images").exists()


def test_never_overwrites_existing_file(tmp_path):
    make(tmp_path / "Images" / "a.png", "old")
    make(tmp_path / "a.png", "new")
    ds.execute(ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES))
    assert (tmp_path / "Images" / "a.png").read_text() == "old"
    assert (tmp_path / "Images" / "a (1).png").read_text() == "new"


def test_no_data_loss_when_two_files_want_the_same_name(tmp_path):
    make(tmp_path / "Images" / "a.png", "old")
    make(tmp_path / "a.png", "new1")
    make(tmp_path / "a (1).png", "new2")
    ds.execute(ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES))
    contents = sorted(p.read_text() for p in (tmp_path / "Images").iterdir())
    assert contents == ["new1", "new2", "old"]


def test_by_date_uses_year_and_month(tmp_path):
    photo = make(tmp_path / "a.png")
    stamp = datetime(2024, 3, 15, 12, 0).timestamp()
    os.utime(photo, (stamp, stamp))
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES, by_date=True)
    assert moves[0][1] == tmp_path / "Images" / "2024" / "03" / "a.png"


def test_undo_removes_nested_empty_folders(tmp_path):
    make(tmp_path / "a.png")
    done = ds.execute(ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES, by_date=True))
    ds.save_history(done)
    assert ds.undo() == 1
    assert (tmp_path / "a.png").exists()
    assert not (tmp_path / "Images").exists()


def test_scan_skips_project_and_hidden_folders(tmp_path):
    make(tmp_path / ".git" / "x.txt")
    make(tmp_path / "node_modules" / "y.txt")
    make(tmp_path / ".venv" / "z.txt")
    make(tmp_path / "keep" / "ok.txt")
    names = [path.name for path, _ in ds.scan([tmp_path])]
    assert names == ["ok.txt"]


def test_find_duplicates_keeps_oldest_and_ignores_empty_files(tmp_path):
    make(tmp_path / "a.txt", "same", age_days=10)
    make(tmp_path / "sub" / "b.txt", "same")
    make(tmp_path / "c.txt", "different")
    make(tmp_path / "e1.txt", "")
    make(tmp_path / "e2.txt", "")
    groups = ds.find_duplicates(ds.scan([tmp_path]))
    assert len(groups) == 1
    assert [path.name for path, _ in groups[0]] == ["a.txt", "b.txt"]


def test_find_old(tmp_path):
    make(tmp_path / "old.txt", age_days=60)
    make(tmp_path / "new.txt", age_days=1)
    old = ds.find_old(ds.scan([tmp_path]), days=30)
    assert [path.name for path, _ in old] == ["old.txt"]


def test_trash_paths_uses_send2trash(tmp_path, monkeypatch):
    target = make(tmp_path / "gone.txt")
    monkeypatch.setattr(ds, "send2trash", lambda p: Path(p).unlink())
    assert ds.trash_paths([target]) == 1
    assert not target.exists()


def test_is_protected():
    assert ds.is_protected(Path.home())
    assert ds.is_protected(Path("C:/Windows/System32"))
    assert not ds.is_protected(Path.home() / "Downloads")




def test_scan_skips_game_data_and_project_folders(tmp_path):
    make(tmp_path / "My Games" / "Rocket League" / "cache.txt")
    make(tmp_path / "myproject" / "package.json")
    make(tmp_path / "myproject" / "src" / "index.js")
    make(tmp_path / "repo" / ".git" / "HEAD")
    make(tmp_path / "repo" / "main.py")
    make(tmp_path / "keep" / "ok.txt")
    assert [path.name for path, _ in ds.scan([tmp_path])] == ["ok.txt"]