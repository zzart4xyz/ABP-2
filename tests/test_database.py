from __future__ import annotations

import importlib
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TECHHOME_DIR = ROOT_DIR / "TechHome"
if str(TECHHOME_DIR) not in sys.path:
    sys.path.insert(0, str(TECHHOME_DIR))


@pytest.fixture()
def database_module(tmp_path, monkeypatch):
    """Return a fresh instance of the database module using temp files."""

    module = importlib.import_module("database")
    module = importlib.reload(module)
    users_db = tmp_path / "techhome_users.sql"
    monkeypatch.setattr(module, "USERS_DB_PATH", str(users_db))
    monkeypatch.setattr(module, "DATA_DB_DIR", str(tmp_path))
    yield module
    if users_db.exists():
        os.remove(users_db)


def test_create_user_rejects_blank_credentials(database_module):
    db = database_module
    assert db.create_user("   ", "password") is False
    assert db.create_user("alice", "   ") is False
    assert not Path(db.USERS_DB_PATH).exists()
    assert not Path(db.get_user_db_path("   ")).exists()


def test_create_and_authenticate_user(database_module):
    db = database_module
    assert db.create_user("alice", "secret-pass") is True
    assert db.authenticate("alice", "secret-pass") is True
    assert db.authenticate("alice", "wrong") is False

    user_db = Path(db.get_user_db_path("alice"))
    assert user_db.exists()
    with sqlite3.connect(user_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='actions'"
        )
        assert cursor.fetchone() is not None


def test_authenticate_rejects_blank_credentials(database_module):
    db = database_module
    assert db.authenticate("", "password") is False
    assert db.authenticate("alice", "") is False


def test_get_user_db_path_sanitises_username(database_module, tmp_path):
    db = database_module
    username = "../malicious user"
    path = Path(db.get_user_db_path(username))
    assert path.parent == tmp_path
    assert path.name.startswith("techhome_data_")
    assert path.suffix == ".sql"
    suffix = path.stem.replace("techhome_data_", "")
    assert len(suffix) == 64
    int(suffix, 16)


def test_get_user_db_path_uses_legacy_file_if_present(database_module, tmp_path):
    db = database_module
    username = "legacy user"
    legacy_path = tmp_path / f"techhome_data_{username}.sql"
    legacy_path.write_text("")

    resolved = Path(db.get_user_db_path(username))
    assert resolved == legacy_path


def test_create_user_creates_safe_filename(database_module, tmp_path):
    db = database_module
    username = "../bob"
    assert db.create_user(username, "secret") is True

    path = Path(db.get_user_db_path(username))
    assert path.parent == tmp_path
    assert path.exists()
    expected_suffix = hashlib.sha256(username.encode("utf-8")).hexdigest()
    assert path.stem == f"techhome_data_{expected_suffix}"
