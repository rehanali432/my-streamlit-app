"""Database operations for PatternProof using sqlite3.

Stores delivery order incident evidence, order details, platforms, stores,
amounts, refund statuses, and link groups.
"""

import sqlite3
import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Generator

DB_FILE = "patternproof.db"

VALID_ISSUE_TYPES = [
    "Late delivery",
    "Missing item",
    "Wrong item",
    "Damaged/spoiled",
    "Refund not received",
    "Refund denied",
    "Support unresponsive",
    "Other",
]

VALID_REFUND_STATUSES = [
    "None requested",
    "Pending",
    "Partial",
    "Full",
    "Denied",
]


@contextmanager
def db_session(db_path: str = DB_FILE) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing a sqlite3 connection that closes cleanly."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str = DB_FILE) -> None:
    """Initialize database and migrate table if necessary."""
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if table exists and inspect columns
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("PRAGMA table_info(incidents)")
            columns = [row["name"] for row in cursor.fetchall()]
            # Migration check: if old schema columns exist, drop and recreate
            if "order_date" not in columns or "restaurant_or_store" not in columns:
                cursor.execute("DROP TABLE incidents")
                table_exists = False

        if not table_exists:
            cursor.execute(
                """
                CREATE TABLE incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_name TEXT NOT NULL,
                    order_date TEXT,
                    platform TEXT NOT NULL,
                    restaurant_or_store TEXT NOT NULL,
                    order_id TEXT,
                    issue_type TEXT NOT NULL,
                    amount_inr REAL,
                    promised_minutes INTEGER,
                    actual_minutes INTEGER,
                    refund_status TEXT NOT NULL DEFAULT 'None requested',
                    extracted_text TEXT,
                    notes TEXT,
                    image_path TEXT,
                    file_hash TEXT,
                    link_group TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )


def add_incident(
    case_name: str,
    order_date: Optional[str],
    platform: str,
    restaurant_or_store: str,
    order_id: Optional[str],
    issue_type: str,
    amount_inr: Optional[float],
    promised_minutes: Optional[int],
    actual_minutes: Optional[int],
    refund_status: str = "None requested",
    extracted_text: str = "",
    notes: str = "",
    image_path: str = "",
    file_hash: str = "",
    link_group: Optional[str] = None,
    created_at: Optional[str] = None,
    db_path: str = DB_FILE,
) -> int:
    """Insert a new delivery order incident record and return its id."""
    if created_at is None:
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    init_db(db_path)

    # Sanitize inputs
    clean_case = case_name.strip() if case_name else "Default Case"
    clean_date = order_date.strip() if order_date and order_date.strip() else None
    clean_platform = platform.strip() if platform else "Other"
    clean_store = restaurant_or_store.strip() if restaurant_or_store else "Store Not Specified"
    clean_order_id = order_id.strip() if order_id and order_id.strip() else None
    clean_issue = issue_type if issue_type in VALID_ISSUE_TYPES else "Other"
    clean_refund = refund_status if refund_status in VALID_REFUND_STATUSES else "None requested"
    clean_link = link_group.strip() if link_group and link_group.strip() else None

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO incidents (
                case_name, order_date, platform, restaurant_or_store,
                order_id, issue_type, amount_inr, promised_minutes,
                actual_minutes, refund_status, extracted_text, notes,
                image_path, file_hash, link_group, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_case,
                clean_date,
                clean_platform,
                clean_store,
                clean_order_id,
                clean_issue,
                amount_inr,
                promised_minutes,
                actual_minutes,
                clean_refund,
                extracted_text or "",
                notes or "",
                image_path or "",
                file_hash or "",
                clean_link,
                created_at,
            ),
        )
        return cursor.lastrowid


def get_incidents(
    case_name: Optional[str] = None,
    link_group: Optional[str] = None,
    platform: Optional[str] = None,
    db_path: str = DB_FILE,
) -> List[Dict[str, Any]]:
    """Retrieve all incidents with optional filtering, sorted chronologically."""
    init_db(db_path)
    query = "SELECT * FROM incidents WHERE 1=1"
    params: List[Any] = []

    if case_name:
        query += " AND case_name = ?"
        params.append(case_name)

    if link_group:
        query += " AND link_group = ?"
        params.append(link_group)

    if platform:
        query += " AND platform = ?"
        params.append(platform)

    # Sort dated orders first chronologically, undated at end
    query += " ORDER BY CASE WHEN order_date IS NULL OR order_date = '' THEN 1 ELSE 0 END, order_date ASC, id ASC"

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_incident_by_id(incident_id: int, db_path: str = DB_FILE) -> Optional[Dict[str, Any]]:
    """Fetch a single incident by its ID."""
    init_db(db_path)
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_incident(
    incident_id: int,
    case_name: str,
    order_date: Optional[str],
    platform: str,
    restaurant_or_store: str,
    order_id: Optional[str],
    issue_type: str,
    amount_inr: Optional[float],
    promised_minutes: Optional[int],
    actual_minutes: Optional[int],
    refund_status: str,
    extracted_text: str,
    notes: str,
    image_path: str,
    file_hash: str,
    link_group: Optional[str],
    db_path: str = DB_FILE,
) -> bool:
    """Update an existing incident record."""
    clean_case = case_name.strip() if case_name else "Default Case"
    clean_date = order_date.strip() if order_date and order_date.strip() else None
    clean_platform = platform.strip() if platform else "Other"
    clean_store = restaurant_or_store.strip() if restaurant_or_store else "Store Not Specified"
    clean_order_id = order_id.strip() if order_id and order_id.strip() else None
    clean_issue = issue_type if issue_type in VALID_ISSUE_TYPES else "Other"
    clean_refund = refund_status if refund_status in VALID_REFUND_STATUSES else "None requested"
    clean_link = link_group.strip() if link_group and link_group.strip() else None

    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE incidents
            SET case_name = ?,
                order_date = ?,
                platform = ?,
                restaurant_or_store = ?,
                order_id = ?,
                issue_type = ?,
                amount_inr = ?,
                promised_minutes = ?,
                actual_minutes = ?,
                refund_status = ?,
                extracted_text = ?,
                notes = ?,
                image_path = ?,
                file_hash = ?,
                link_group = ?
            WHERE id = ?
            """,
            (
                clean_case,
                clean_date,
                clean_platform,
                clean_store,
                clean_order_id,
                clean_issue,
                amount_inr,
                promised_minutes,
                actual_minutes,
                clean_refund,
                extracted_text or "",
                notes or "",
                image_path or "",
                file_hash or "",
                clean_link,
                incident_id,
            ),
        )
        return cursor.rowcount > 0


def update_link_groups_for_ids(
    incident_ids: List[int],
    link_group: Optional[str],
    db_path: str = DB_FILE,
) -> int:
    """Batch assign a link group to a list of incident IDs."""
    if not incident_ids:
        return 0
    group_val = link_group.strip() if link_group and link_group.strip() else None
    placeholders = ",".join("?" for _ in incident_ids)
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE incidents SET link_group = ? WHERE id IN ({placeholders})",
            [group_val] + incident_ids,
        )
        return cursor.rowcount


def delete_incident(incident_id: int, db_path: str = DB_FILE) -> bool:
    """Delete a single incident by ID."""
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
        return cursor.rowcount > 0


def delete_all_incidents(case_name: Optional[str] = None, db_path: str = DB_FILE) -> int:
    """Delete all incidents (optionally only within a specific case)."""
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        if case_name:
            cursor.execute("DELETE FROM incidents WHERE case_name = ?", (case_name,))
        else:
            cursor.execute("DELETE FROM incidents")
        return cursor.rowcount


def get_case_names(db_path: str = DB_FILE) -> List[str]:
    """Return all unique case names in the database."""
    init_db(db_path)
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT case_name FROM incidents ORDER BY case_name ASC")
        rows = cursor.fetchall()
        names = [row["case_name"] for row in rows if row["case_name"]]
        return names if names else ["Delivery Orders Case"]


def get_link_groups(case_name: Optional[str] = None, db_path: str = DB_FILE) -> List[str]:
    """Return all unique non-null link groups."""
    init_db(db_path)
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        if case_name:
            cursor.execute(
                "SELECT DISTINCT link_group FROM incidents WHERE case_name = ? AND link_group IS NOT NULL AND link_group != '' ORDER BY link_group ASC",
                (case_name,),
            )
        else:
            cursor.execute(
                "SELECT DISTINCT link_group FROM incidents WHERE link_group IS NOT NULL AND link_group != '' ORDER BY link_group ASC"
            )
        rows = cursor.fetchall()
        return [row["link_group"] for row in rows if row["link_group"]]


def get_platforms(case_name: Optional[str] = None, db_path: str = DB_FILE) -> List[str]:
    """Return all unique platforms recorded."""
    init_db(db_path)
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        if case_name:
            cursor.execute(
                "SELECT DISTINCT platform FROM incidents WHERE case_name = ? AND platform IS NOT NULL AND platform != '' ORDER BY platform ASC",
                (case_name,),
            )
        else:
            cursor.execute(
                "SELECT DISTINCT platform FROM incidents WHERE platform IS NOT NULL AND platform != '' ORDER BY platform ASC"
            )
        rows = cursor.fetchall()
        return [row["platform"] for row in rows if row["platform"]]
