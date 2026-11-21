from pathlib import Path

import pytest

import downloads_sorter as ds


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "HISTORY_FILE", tmp_path / "history.json")


def test_category_for_known_and_unknown():
    cats = ds.DEFAULT_CATEGORIES
    assert ds.category_for(Path("photo.PNG"), cats) == "Images"
    assert ds.category_for(Path("song.mp3"), cats) == "Audio"
    assert ds.category_for(Path("weird.xyz"), cats) == "Other"


def test_unique_destination_adds_counter(tmp_path):
    (tmp_path / "a.png").write_text("x")
    assert ds.unique_destination(tmp_path / "a.png") == tmp_path / "a (1).png"
    (tmp_path / "a (1).png").write_text("x")
    assert ds.unique_destination(tmp_path / "a.png") == tmp_path / "a (2).png"


def test_plan_skips_folders_hidden_and_incomplete(tmp_path):
    (tmp_path / "keep.png").write_text("x")
    (tmp_path / ".hidden.png").write_text("x")
    (tmp_path / "busy.crdownload").write_text("x")
    (tmp_path / "somefolder").mkdir()
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES)
    assert [src.name for src, _ in moves] == ["keep.png"]


def test_plan_skips_system_files(tmp_path):
    (tmp_path / "desktop.ini").write_text("x")
    (tmp_path / "Thumbs.db").write_text("x")
    (tmp_path / "song.mp3").write_text("x")
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES)
    assert [src.name for src, _ in moves] == ["song.mp3"]


def test_execute_and_undo_roundtrip(tmp_path):
    (tmp_path / "a.png").write_text("img")
    (tmp_path / "b.mp3").write_text("song")
    moves = ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES)
    done = ds.execute(moves)
    ds.save_history(done)

    assert (tmp_path / "Images" / "a.png").exists()
    assert (tmp_path / "Audio" / "b.mp3").exists()

    assert ds.undo() == 2
    assert (tmp_path / "a.png").exists()
    assert (tmp_path / "b.mp3").exists()
    assert not (tmp_path / "Images").exists()


def test_never_overwrites_existing_file(tmp_path):
    (tmp_path / "Images").mkdir()
    (tmp_path / "Images" / "a.png").write_text("old")
    (tmp_path / "a.png").write_text("new")
    ds.execute(ds.plan_moves(tmp_path, ds.DEFAULT_CATEGORIES))
    assert (tmp_path / "Images" / "a.png").read_text() == "old"
    assert (tmp_path / "Images" / "a (1).png").read_text() == "new"