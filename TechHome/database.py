"""
database.py
-------------

This module provides a simple SQLite-based user store for login and
registration.  It uses Python's built-in ``sqlite3`` library to manage
a local database file located alongside the application code.  The
database is initialised on demand and includes a single table
``users`` with ``username`` and ``password`` fields.  Passwords are
stored in plain text for simplicity; in a real-world application you
should use password hashing (e.g. bcrypt or hashlib.pbkdf2_hmac).

Functions
~~~~~~~~~

``init_db()``
    Ensure the database and ``users`` table exist.

``create_user(username, password)``
    Attempt to create a new user.  Returns ``True`` on success and
    ``False`` if the username already exists.

``authenticate(username, password)``
    Check whether a given username/password pair exists.  Returns
    ``True`` for a valid login and ``False`` otherwise.

"""

import sqlite3
import os
import hashlib
import importlib
from typing import Optional


class _DummyArgon2Exceptions:
    VerifyMismatchError = Exception
    VerificationError = Exception


argon2_exceptions = _DummyArgon2Exceptions()
PasswordHasher = None
_ph = None

try:
    argon2_module = importlib.import_module("argon2")
except ImportError:
    argon2_module = None
else:
    PasswordHasher = getattr(argon2_module, "PasswordHasher", None)
    argon2_exceptions = getattr(argon2_module, "exceptions", argon2_exceptions)
    if PasswordHasher is not None:
        try:
            # Configure Argon2id parameters.  memory_cost is in kibibytes.
            _ph = PasswordHasher(memory_cost=64 * 1024, time_cost=3, parallelism=1)
        except Exception:
            _ph = None


# -----------------------------------------------------------------------------
# Database paths
#
# User credentials (usernames and passwords) are stored in a single shared
# database file (``techhome_users.sql``) located in the same directory as
# this module.  Each user's personal data (device states, lists, notes,
# reminders, alarms, timers and action logs) are stored in a separate
# database file named ``techhome_data_<username>.sql`` in the same directory.
# This separation ensures that no user's data is mixed with another's and
# allows per‑user data to be easily managed.

# Central database for user credentials
USERS_DB_FILENAME = "techhome_users.sql"
USERS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), USERS_DB_FILENAME)

# Directory where per‑user databases are stored.  By default, this is the
# directory containing this module.  A helper function computes the full
# path to a specific user's database file.
DATA_DB_DIR = os.path.dirname(os.path.abspath(__file__))

def get_user_db_path(username: str) -> str:
    """
    Return the file path for a given user's data database.

    The username is incorporated directly into the filename.  Special
    characters are not escaped because usernames are expected to be simple
    alphanumeric strings.  In a production environment you should
    sanitise or hash usernames to avoid conflicts or path traversal.

    Parameters
    ----------
    username: str
        The plain‑text username associated with the data database.

    Returns
    -------
    str
        The absolute path to the user's data database file.
    """
    return os.path.join(DATA_DB_DIR, f"techhome_data_{username}.sql")


def init_db() -> None:
    """
    Initialise the central users database.  This function ensures that
    the ``users`` table exists and contains the expected columns.  It
    does not create any per‑user tables; those are created on demand
    via ``init_user_db`` when storing user‑specific data.
    """
    conn = sqlite3.connect(USERS_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "username_hash TEXT UNIQUE,"
        "password_hash TEXT,"
        "salt BLOB,"
        "algo TEXT"
        ")"
    )
    # Verify presence of expected columns; add them if missing.  This
    # allows upgrading from earlier schema versions without dropping
    # existing data.  SQLite only permits adding new columns via ALTER TABLE.
    cur.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cur.fetchall()]
    if 'salt' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN salt BLOB")
    if 'algo' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN algo TEXT")
    conn.commit()
    conn.close()


def init_user_db(username: str) -> None:
    """
    Initialise the per‑user database for the given username.  This
    function creates all necessary tables if they do not already exist.
    It is safe to call this multiple times; subsequent calls have
    no effect once the tables are created.

    Parameters
    ----------
    username: str
        The plain‑text username identifying the data database.  The
        tables created are scoped to this database and will not
        affect other users.
    """
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # Table for recording actions performed by this user
    cur.execute(
        "CREATE TABLE IF NOT EXISTS actions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "action TEXT,"
        "timestamp TEXT"
        ")"
    )
    # Device states specific to this user
    cur.execute(
        "CREATE TABLE IF NOT EXISTS device_states ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "device_name TEXT,"
        "group_name TEXT,"
        "state INTEGER,"
        "UNIQUE(device_name)"
        ")"
    )
    # Lists names
    cur.execute(
        "CREATE TABLE IF NOT EXISTS user_lists ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "list_name TEXT UNIQUE"
        ")"
    )
    # Items within lists
    cur.execute(
        "CREATE TABLE IF NOT EXISTS list_items ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "list_name TEXT,"
        "item_text TEXT,"
        "item_order INTEGER"
        ")"
    )
    # Notes with positions
    cur.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "text TEXT,"
        "timestamp TEXT,"
        "cell_row INTEGER,"
        "cell_col INTEGER"
        ")"
    )
    # Reminders
    cur.execute(
        "CREATE TABLE IF NOT EXISTS reminders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "datetime TEXT,"
        "text TEXT"
        ")"
    )
    # Alarms
    cur.execute(
        "CREATE TABLE IF NOT EXISTS alarms ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "datetime TEXT,"
        "text TEXT"
        ")"
    )
    # Timers
    cur.execute(
        "CREATE TABLE IF NOT EXISTS timers ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "end_time TEXT,"
        "text TEXT"
        ")"
    )

    # Notifications
    # This table stores timestamp/message pairs representing the
    # notifications shown to the user.  An auto‑increment primary key
    # allows ordering and pruning of old notifications.
    cur.execute(
        "CREATE TABLE IF NOT EXISTS notifications ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "timestamp TEXT,"
        "message TEXT"
        ")"
    )

    # Renamed devices
    # This table keeps a mapping from a device's current (renamed) name
    # back to its original base name.  Storing this mapping makes it
    # possible to persist the icon associated with a device even if the
    # user changes its name.  Each new_name is unique.
    cur.execute(
        "CREATE TABLE IF NOT EXISTS renamed_devices ("
        "new_name TEXT PRIMARY KEY,"
        "original_name TEXT"
        ")"
    )

    # User settings
    #
    # To persist user preferences such as theme (dark/light), language
    # selection, time format (24h/12h), notification toggle, device
    # filter choice and sort order, we create a simple key/value table.
    # Each user has an independent ``settings`` table within their
    # personal database.  Keys are unique so inserting a duplicate
    # key replaces the existing value via ON CONFLICT clause.  Storing
    # settings separately from user credentials ensures that no
    # personal information leaks into the global user database and
    # allows per‑user preferences to be restored on login.
    cur.execute(
        "CREATE TABLE IF NOT EXISTS settings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "key TEXT UNIQUE,"
        "value TEXT"
        ")"
    )
    conn.commit()
    conn.close()


def log_action(username: str, action: str) -> None:
    """
    Record a user action in the per‑user ``actions`` table.

    Each call inserts a new row into the ``actions`` table within the
    user's personal database with a description of the action and the
    current timestamp (ISO 8601 format).  The user's database is
    initialised on demand if it does not already exist.

    Parameters
    ----------
    username: str
        The username associated with the action.  This value is only
        used to determine which database file to open; it is not
        stored within the actions table itself because the table is
        scoped to a single user.
    action: str
        A brief description of the action performed by the user.
    """
    init_user_db(username)
    from datetime import datetime
    ts = datetime.now().isoformat()
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO actions (action, timestamp) VALUES (?, ?)",
        (action, ts)
    )
    conn.commit()
    conn.close()


def get_action_count(username: str) -> int:
    """
    Return the number of actions recorded for the specified user.

    This helper reads the ``actions`` table from the user's personal
    database and returns the row count.  Because the actions table is
    scoped to a single user, no username filter is necessary.

    Parameters
    ----------
    username: str
        The plain‑text username whose actions should be counted.

    Returns
    -------
    int
        The number of action records stored for the user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM actions")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

# Additional helper functions
# -----------------------------------------------------------------------------
def get_recent_actions(username: str, limit: int = 5) -> list[tuple[str, str]]:
    """
    Retrieve the most recent actions performed by the user.

    This function returns a list of (action, timestamp) tuples for the
    specified user, ordered from most recent to oldest.  The number of
    entries returned is controlled by the ``limit`` parameter.  If the
    user has fewer than ``limit`` actions recorded, all available
    actions are returned.

    Parameters
    ----------
    username: str
        The plain‑text username whose recent actions should be
        retrieved.
    limit: int, optional
        The maximum number of action records to return.  Defaults to
        5.  Set to a larger value to retrieve more history.

    Returns
    -------
    list of tuple(str, str)
        A list of (action, timestamp) tuples.  The timestamp is
        returned as an ISO‑formatted string.  The list is sorted so
        that the most recently recorded action appears first.  An
        empty list is returned if the user has no recorded actions or
        if an error occurs.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        # Order by descending id to get most recent actions first
        cur.execute(
            "SELECT action, timestamp FROM actions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()
        return [(str(action), str(ts)) for action, ts in rows]
    except Exception:
        # On any exception return an empty list
        return []


# -----------------------------------------------------------------------------
# Persistent state for devices, lists, notes, reminders, alarms and timers
# -----------------------------------------------------------------------------

def save_device_state(username: str, device_name: str, group_name: str, state: bool) -> None:
    """
    Insert or update the on/off state of a device for a specific user.

    For per‑user databases, the device name uniquely identifies the
    record.  When the same device name is inserted again, the group
    and state are updated.  The user's data database is created on
    demand if it does not already exist.

    Parameters
    ----------
    username: str
        The owner of the device state record.  Used to determine which
        database file to open.
    device_name: str
        The name of the device.  This field uniquely identifies the
        record within the user's database.
    group_name: str
        The group the device belongs to.
    state: bool
        ``True`` if the device is on; ``False`` if off.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO device_states (device_name, group_name, state) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(device_name) DO UPDATE SET group_name=excluded.group_name, state=excluded.state",
        (device_name, group_name, int(state))
    )
    conn.commit()
    conn.close()


def get_device_states(username: str) -> list[tuple[str, str, bool]]:
    """
    Retrieve device states for the specified user.

    Reads from the user's personal database and returns a list of
    ``(device_name, group_name, state)`` tuples.  If no devices have
    been stored, an empty list is returned.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "SELECT device_name, group_name, state FROM device_states"
    )
    rows = cur.fetchall()
    conn.close()
    return [(name, grp, bool(st)) for name, grp, st in rows]


def save_list(username: str, list_name: str) -> None:
    """
    Persist a list name for the specified user.  If the list already
    exists, the operation does nothing.  The list is stored in the
    user's personal database; list names are unique within that
    database.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO user_lists (list_name) VALUES (?)",
            (list_name,)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # List already exists
        pass
    finally:
        conn.close()


def delete_list(username: str, list_name: str) -> None:
    """
    Remove a list and all its items for the specified user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("DELETE FROM list_items WHERE list_name=?", (list_name,))
    cur.execute("DELETE FROM user_lists WHERE list_name=?", (list_name,))
    conn.commit()
    conn.close()


def get_lists(username: str) -> list[str]:
    """
    Return the list names for the given user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT list_name FROM user_lists ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_list_item(username: str, list_name: str, item_text: str, order: int) -> None:
    """
    Persist an item for a user's list.  Items are not unique and may appear
    multiple times.  The ``order`` parameter determines the display order.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO list_items (list_name, item_text, item_order) VALUES (?, ?, ?)",
        (list_name, item_text, order)
    )
    conn.commit()
    conn.close()


def delete_list_item(username: str, list_name: str, item_text: str) -> None:
    """
    Delete a single occurrence of an item from a user's list.  If
    multiple identical items exist, only one is removed.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # Delete the first matching item using a subquery to limit the delete
    cur.execute(
        "DELETE FROM list_items WHERE id IN ("
        "SELECT id FROM list_items WHERE list_name=? AND item_text=? ORDER BY id LIMIT 1"
        ")",
        (list_name, item_text)
    )
    conn.commit()
    conn.close()


def get_list_items(username: str, list_name: str) -> list[str]:
    """
    Return the items for a specific user's list.  Items are ordered
    descending by their ``item_order`` so that newly added items
    appear first.  When multiple items share the same order, the row
    ``id`` is used to maintain insertion order.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "SELECT item_text FROM list_items WHERE list_name=? ORDER BY item_order DESC, id DESC",
        (list_name,)
    )
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_note(username: str, text: str, timestamp: str, row: int, col: int) -> None:
    """
    Persist a note for the specified user.  Notes are appended to the
    database and do not update existing entries.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (text, timestamp, cell_row, cell_col) VALUES (?, ?, ?, ?)",
        (text, timestamp, row, col)
    )
    conn.commit()
    conn.close()


def get_notes(username: str) -> list[tuple[str, str, int, int]]:
    """
    Retrieve all notes for a user.  Returns a list of tuples
    ``(text, timestamp, row, col)``.  The order reflects insertion order.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "SELECT text, timestamp, cell_row, cell_col FROM notes ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return [(text, ts, int(r), int(c)) for text, ts, r, c in rows]


def save_reminder(username: str, dt: str, text: str) -> None:
    """
    Persist a reminder for a user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (datetime, text) VALUES (?, ?)",
        (dt, text)
    )
    conn.commit()
    conn.close()


def delete_reminder(username: str, dt: str, text: str) -> None:
    """
    Delete a specific reminder for a user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM reminders WHERE datetime=? AND text=?",
        (dt, text)
    )
    conn.commit()
    conn.close()


def get_reminders(username: str) -> list[tuple[str, str]]:
    """
    Retrieve all reminders for a user.  Returns a list of (datetime, text).
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT datetime, text FROM reminders ORDER BY datetime")
    rows = cur.fetchall()
    conn.close()
    return [(dt, txt) for dt, txt in rows]


def save_alarm(username: str, dt: str, text: str) -> None:
    """
    Persist an alarm for a user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO alarms (datetime, text) VALUES (?, ?)",
        (dt, text)
    )
    conn.commit()
    conn.close()


def delete_alarm(username: str, dt: str, text: str) -> None:
    """
    Delete an alarm for a user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM alarms WHERE datetime=? AND text=?",
        (dt, text)
    )
    conn.commit()
    conn.close()


def get_alarms(username: str) -> list[tuple[str, str]]:
    """
    Retrieve all alarms for a user.  Returns a list of (datetime, text).
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT datetime, text FROM alarms ORDER BY datetime")
    rows = cur.fetchall()
    conn.close()
    return [(dt, txt) for dt, txt in rows]


def save_timer(username: str, end_time: str, text: str) -> None:
    """
    Persist a timer for a user.  The end_time should be an ISO
    formatted string.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO timers (end_time, text) VALUES (?, ?)",
        (end_time, text)
    )
    conn.commit()
    conn.close()


def delete_timer(username: str, end_time: str, text: str) -> None:
    """
    Delete a timer for a user.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM timers WHERE end_time=? AND text=?",
        (end_time, text)
    )
    conn.commit()
    conn.close()


def get_timers(username: str) -> list[tuple[str, str]]:
    """
    Retrieve all timers for a user.  Returns a list of (end_time, text).
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT end_time, text FROM timers ORDER BY end_time")
    rows = cur.fetchall()
    conn.close()
    return [(et, txt) for et, txt in rows]

# -----------------------------------------------------------------------------
# Notifications and renamed devices persistence
# -----------------------------------------------------------------------------

def save_notification(username: str, timestamp: str, message: str) -> None:
    """
    Persist a notification and prune the oldest entries.

    A notification consists of a timestamp and a message.  When storing
    a new notification, the total count is limited to a maximum.  If
    more than ``MAX_NOTIFICATIONS`` notifications exist, the oldest
    notifications are deleted to keep only the most recent ones.

    Parameters
    ----------
    username: str
        The user whose notification history should be updated.
    timestamp: str
        A human‑readable timestamp string (e.g. "HH:MM" or "HH:MM:SS").
    message: str
        The notification message to store.
    """
    # Avoid importing PyQt dependencies from constants in headless contexts
    try:
        from constants import MAX_NOTIFICATIONS  # type: ignore
    except Exception:
        MAX_NOTIFICATIONS = 100
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO notifications (timestamp, message) VALUES (?, ?)",
            (timestamp, message),
        )
        cur.execute("SELECT COUNT(*) FROM notifications")
        row = cur.fetchone()
        count = row[0] if row else 0
        if count > MAX_NOTIFICATIONS:
            excess = count - MAX_NOTIFICATIONS
            cur.execute(
                "DELETE FROM notifications WHERE id IN ("
                "SELECT id FROM notifications ORDER BY id ASC LIMIT ?"
                ")",
                (excess,),
            )
        conn.commit()
    finally:
        conn.close()


def get_notifications(username: str, limit: int | None = None) -> list[tuple[str, str]]:
    """
    Retrieve notifications for a user.

    The notifications are returned as a list of (timestamp, message) tuples
    sorted from oldest to newest.  If ``limit`` is provided, only the most
    recent ``limit`` notifications are returned.  If no notifications exist
    or an error occurs, an empty list is returned.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        if limit is None:
            cur.execute("SELECT timestamp, message FROM notifications ORDER BY id ASC")
            rows = cur.fetchall()
        else:
            cur.execute(
                "SELECT timestamp, message FROM notifications ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()[::-1]
        conn.close()
        return [(str(ts), str(msg)) for ts, msg in rows]
    except Exception:
        return []


def rename_device(username: str, old_name: str, new_name: str) -> None:
    """
    Update the name of a device in the ``device_states`` table.

    This helper simply replaces the device_name of a record.  It does not
    alter the group or state of the device, nor does it update any
    notifications or mappings.  The caller is responsible for updating
    related tables (e.g. renamed_devices or notifications) via other
    functions.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE device_states SET device_name=? WHERE device_name=?",
            (new_name, old_name),
        )
        conn.commit()
    finally:
        conn.close()


def update_renamed_device(username: str, old_name: str, new_name: str) -> None:
    """
    Record a mapping from a renamed device's new name to its original base name.

    When a device is renamed, its icon should remain associated with the
    original base name.  This function stores or updates the mapping in
    the ``renamed_devices`` table.  If a mapping already exists for
    ``old_name``, the original base name from that mapping is reused.
    Otherwise, ``old_name`` itself is considered the original.  Any
    existing mapping for ``new_name`` is overwritten.  Mappings for
    ``old_name`` are removed.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        # Determine original name for the old mapping
        cur.execute(
            "SELECT original_name FROM renamed_devices WHERE new_name=?",
            (old_name,),
        )
        row = cur.fetchone()
        original = row[0] if row else old_name
        # Remove any existing mappings for new_name and old_name
        cur.execute("DELETE FROM renamed_devices WHERE new_name IN (?, ?)", (new_name, old_name))
        # Insert new mapping
        cur.execute(
            "INSERT INTO renamed_devices (new_name, original_name) VALUES (?, ?)",
            (new_name, original),
        )
        conn.commit()
    finally:
        conn.close()


def get_renamed_devices(username: str) -> dict[str, str]:
    """
    Fetch all renamed device mappings for a user.

    Returns a dictionary mapping each ``new_name`` to its corresponding
    ``original_name``.  If an error occurs, an empty dictionary is returned.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT new_name, original_name FROM renamed_devices")
        rows = cur.fetchall()
        conn.close()
        return {str(n): str(o) for n, o in rows}
    except Exception:
        return {}


def get_original_device_name(username: str, name: str) -> str | None:
    """
    Return the original base name for a device if it has been renamed.

    If the provided ``name`` appears in the ``renamed_devices`` table,
    the stored original name is returned.  Otherwise, ``None`` is
    returned.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(
            "SELECT original_name FROM renamed_devices WHERE new_name=?",
            (name,),
        )
        row = cur.fetchone()
        conn.close()
        return str(row[0]) if row else None
    except Exception:
        return None


def update_notification_names(username: str, old_name: str, new_name: str) -> None:
    """
    Replace occurrences of a device name in saved notifications.

    This function performs a simple text replacement of ``old_name`` with
    ``new_name`` in the ``message`` column of the ``notifications`` table.
    Only rows containing the old name are affected.  Use with care if
    device names could be substrings of other unrelated text.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE notifications SET message = REPLACE(message, ?, ?) "
            "WHERE instr(message, ?) > 0",
            (old_name, new_name, old_name),
        )
        conn.commit()
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# User settings persistence
# -----------------------------------------------------------------------------

def save_setting(username: str, key: str, value: str) -> None:
    """
    Persist a single user preference.

    This helper inserts or updates a key/value pair in the ``settings``
    table of the given user's data database.  If the key already
    exists, its value is replaced.  The per‑user database is
    initialised on demand.

    Parameters
    ----------
    username: str
        The username whose settings file should be modified.  Used
        solely to locate the correct database file.
    key: str
        The setting name (e.g. ``"theme"``, ``"language"``).
    value: str
        The string representation of the setting value.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # Use INSERT ... ON CONFLICT to update existing settings
    cur.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_setting(username: str, key: str, default: str | None = None) -> Optional[str]:
    """
    Retrieve the value of a user setting.

    If the requested key does not exist in the user's settings table,
    the provided default value is returned.  The per‑user database is
    created if necessary.

    Parameters
    ----------
    username: str
        The username associated with the settings.
    key: str
        The setting name to look up.
    default: str or None, optional
        The value to return when the key is not present.  Defaults to
        ``None``.

    Returns
    -------
    str or None
        The stored setting value, or the default if the key is
        missing.
    """
    init_user_db(username)
    path = get_user_db_path(username)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0]


def create_user(username: str, password: str) -> bool:
    """
    Create a new user with hashed credentials.

    The username is hashed using SHA-256 to avoid storing it in plain
    text.  The password is hashed using PBKDF2-HMAC-SHA256 with a
    unique 16-byte salt for each user.  If the hashed username
    already exists in the database, the function returns ``False``.

    Parameters
    ----------
    username: str
        The username to register.  Usernames are case-sensitive.
    password: str
        The password associated with the account.

    Returns
    -------
    bool
        ``True`` if the user was created successfully; ``False`` if
        the username already exists or an error occurred.
    """
    # Compute the hash of the username.  We use SHA-256 for
    # uniqueness and to avoid storing the plain username.
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    # Ensure the central users database exists
    init_db()
    conn = sqlite3.connect(USERS_DB_PATH)
    cur = conn.cursor()
    # Choose the strongest available algorithm.  If Argon2id support is
    # available, prefer it; otherwise fall back to PBKDF2-HMAC-SHA256
    # with a recommended work factor.  See OWASP guidance for
    # iteration counts【382177254043416†L456-L473】.
    if _ph is not None:
        # Use Argon2id.  The salt is embedded in the hash string, so we
        # store NULL in the salt column.
        password_hash = _ph.hash(password)
        algo = "argon2"
        salt = None
    else:
        # Fall back to PBKDF2-HMAC-SHA256 with 600k iterations.
        salt = os.urandom(16)
        # The work factor (iterations) for PBKDF2-HMAC-SHA256 is set to
        # 600,000, as recommended by OWASP for PBKDF2【382177254043416†L456-L473】.
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 600_000
        ).hex()
        algo = "pbkdf2"
    try:
        cur.execute(
            "INSERT INTO users (username_hash, password_hash, salt, algo) "
            "VALUES (?, ?, ?, ?)",
            (username_hash, password_hash, salt, algo),
        )
        conn.commit()
        # Initialise the per‑user database so that tables exist before
        # the user performs any actions.  If the database already
        # exists (e.g. from a previous run), this call has no effect.
        init_user_db(username)
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    finally:
        conn.close()


def authenticate(username: str, password: str) -> bool:
    """
    Verify a username/password pair against the stored hashes.

    Parameters
    ----------
    username: str
        The username provided by the user.
    password: str
        The password provided by the user.

    Returns
    -------
    bool
        ``True`` if the credentials are valid; ``False`` otherwise.
    """
    username_hash = hashlib.sha256(username.encode("utf-8")).hexdigest()
    # Ensure the central users database exists before authentication
    init_db()
    conn = sqlite3.connect(USERS_DB_PATH)
    cur = conn.cursor()
    # Retrieve the stored password hash for this username
    cur.execute(
        "SELECT password_hash, salt, algo FROM users WHERE username_hash = ?",
        (username_hash,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    stored_pw_hash, salt, algo = row
    # Determine which algorithm to use for verification
    if algo == "argon2":
        if _ph is None:
            # Argon2 support is not available; cannot verify this user.
            return False
        try:
            _ph.verify(stored_pw_hash, password)
            # Ensure the user's data database exists after successful
            # authentication.  This call is idempotent.
            init_user_db(username)
            return True
        except argon2_exceptions.VerifyMismatchError:
            return False
        except argon2_exceptions.VerificationError:
            return False
    elif algo == "pbkdf2":
        # Recompute the PBKDF2 hash using the stored salt and the
        # recommended iteration count (600k) and compare.
        derived_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 600_000
        ).hex()
        if derived_hash == stored_pw_hash:
            init_user_db(username)
            return True
        return False
    else:
        # Unknown algorithm
        return False