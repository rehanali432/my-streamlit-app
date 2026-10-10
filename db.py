"""Database operations for PatternProof: Delivery Evidence Coach.

Stores order details, receipts, and photo checklist verification tasks using SQLite.
All evidence data is saved locally on the user's system.
"""

import os
import json
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any, Set

DB_FILE = "patternproof.db"
UPLOADS_DIR = "uploads"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection with Row factory enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize database tables and create uploads directory if needed."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT,
                platform TEXT,
                order_id TEXT,
                order_date TEXT,
                total_inr REAL,
                items_json TEXT,
                claim_type TEXT,
                receipt_path TEXT,
                receipt_hash TEXT,
                product_photo_path TEXT,
                product_hash TEXT,
                product_analysis_json TEXT,
                created_at TEXT
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_row_id INTEGER NOT NULL,
                task_code TEXT NOT NULL,
                shot_type TEXT NOT NULL,
                title TEXT NOT NULL,
                instruction TEXT NOT NULL,
                angle TEXT NOT NULL,
                must_show_json TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                attempts INTEGER DEFAULT 0,
                photo_path TEXT,
                photo_hash TEXT,
                captured_at TEXT,
                verification_json TEXT,
                updated_at TEXT,
                FOREIGN KEY (order_row_id) REFERENCES orders (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def save_order(data: Dict[str, Any]) -> int:
    """Insert or update an order record. Returns the integer order row id."""
    init_db()
    items_json = json.dumps(data.get("items", []), ensure_ascii=False)
    analysis_json = json.dumps(data.get("product_analysis", {}), ensure_ascii=False)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    order_id = data.get("id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if order_id:
            cursor.execute("""
                UPDATE orders SET
                    store = ?,
                    platform = ?,
                    order_id = ?,
                    order_date = ?,
                    total_inr = ?,
                    items_json = ?,
                    claim_type = ?,
                    receipt_path = ?,
                    receipt_hash = ?,
                    product_photo_path = ?,
                    product_hash = ?,
                    product_analysis_json = ?
                WHERE id = ?
            """, (
                data.get("store"),
                data.get("platform"),
                data.get("order_id"),
                data.get("order_date"),
                data.get("total_inr"),
                items_json,
                data.get("claim_type"),
                data.get("receipt_path"),
                data.get("receipt_hash"),
                data.get("product_photo_path"),
                data.get("product_hash"),
                analysis_json,
                order_id
            ))
            return int(order_id)
        else:
            cursor.execute("""
                INSERT INTO orders (
                    store, platform, order_id, order_date, total_inr, items_json,
                    claim_type, receipt_path, receipt_hash, product_photo_path,
                    product_hash, product_analysis_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("store"),
                data.get("platform"),
                data.get("order_id"),
                data.get("order_date"),
                data.get("total_inr"),
                items_json,
                data.get("claim_type"),
                data.get("receipt_path"),
                data.get("receipt_hash"),
                data.get("product_photo_path"),
                data.get("product_hash"),
                analysis_json,
                now_str
            ))
            conn.commit()
            return cursor.lastrowid


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert an SQLite row to a Python dictionary, decoding JSON columns."""
    d = dict(row)
    if "items_json" in d and d["items_json"]:
        try:
            d["items"] = json.loads(d["items_json"])
        except Exception:
            d["items"] = []
    if "product_analysis_json" in d and d["product_analysis_json"]:
        try:
            d["product_analysis"] = json.loads(d["product_analysis_json"])
        except Exception:
            d["product_analysis"] = {}
    if "must_show_json" in d and d["must_show_json"]:
        try:
            d["must_show"] = json.loads(d["must_show_json"])
        except Exception:
            d["must_show"] = []
    if "verification_json" in d and d["verification_json"]:
        try:
            d["verification"] = json.loads(d["verification_json"])
        except Exception:
            d["verification"] = None
    return d


def get_order(order_row_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve an order by its primary key row ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_row_id,))
        row = cursor.fetchone()
        if row:
            return row_to_dict(row)
    return None


def get_latest_order() -> Optional[Dict[str, Any]]:
    """Retrieve the most recently created order."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row_to_dict(row)
    return None


def list_orders() -> List[Dict[str, Any]]:
    """Return all orders in descending order of ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY id DESC")
        return [row_to_dict(r) for r in cursor.fetchall()]


def save_tasks(order_row_id: int, tasks_list: List[Dict[str, Any]]) -> None:
    """Save or replace all checklist tasks for an order."""
    init_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Remove existing tasks for this order to replace with the fresh validated list
        cursor.execute("DELETE FROM tasks WHERE order_row_id = ?", (order_row_id,))
        for t in tasks_list:
            must_show_json = json.dumps(t.get("must_show", []), ensure_ascii=False)
            cursor.execute("""
                INSERT INTO tasks (
                    order_row_id, task_code, shot_type, title, instruction, angle,
                    must_show_json, status, attempts, photo_path, photo_hash,
                    captured_at, verification_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_row_id,
                t.get("task_code", "T1"),
                t.get("shot_type", "wide_package"),
                t.get("title", ""),
                t.get("instruction", ""),
                t.get("angle", ""),
                must_show_json,
                t.get("status", "Open"),
                t.get("attempts", 0),
                t.get("photo_path"),
                t.get("photo_hash"),
                t.get("captured_at"),
                json.dumps(t.get("verification"), ensure_ascii=False) if t.get("verification") else None,
                now_str
            ))
        conn.commit()


def get_tasks_for_order(order_row_id: int) -> List[Dict[str, Any]]:
    """Retrieve all checklist tasks for an order sorted by task ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE order_row_id = ? ORDER BY id ASC", (order_row_id,))
        return [row_to_dict(r) for r in cursor.fetchall()]


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single checklist task by its primary key ID."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return row_to_dict(row)
    return None


def update_task(task_id: int, fields: Dict[str, Any]) -> None:
    """Update fields on an existing task row."""
    init_db()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields["updated_at"] = now_str

    if "verification" in fields and fields["verification"] is not None:
        fields["verification_json"] = json.dumps(fields.pop("verification"), ensure_ascii=False)

    keys = [k for k in fields.keys() if k != "id"]
    values = [fields[k] for k in keys]
    set_clause = ", ".join([f"{k} = ?" for k in keys])

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", (*values, task_id))
        conn.commit()


def get_order_hashes(order_row_id: int, exclude_task_id: Optional[int] = None) -> Set[str]:
    """Return all known SHA-256 photo hashes in an order to prevent duplicate uploads."""
    hashes: Set[str] = set()
    order = get_order(order_row_id)
    if order:
        if order.get("receipt_hash"):
            hashes.add(order["receipt_hash"])
        if order.get("product_hash"):
            hashes.add(order["product_hash"])

    tasks = get_tasks_for_order(order_row_id)
    for t in tasks:
        if exclude_task_id and t.get("id") == exclude_task_id:
            continue
        if t.get("photo_hash"):
            hashes.add(t["photo_hash"])

    return hashes


def delete_all_data() -> None:
    """Clear all records from database tables and delete uploaded files."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM orders")
        conn.commit()

    if os.path.exists(UPLOADS_DIR):
        for item in os.listdir(UPLOADS_DIR):
            item_path = os.path.join(UPLOADS_DIR, item)
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception:
                pass
