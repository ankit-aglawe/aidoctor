from typing import Any
import sqlite3


def get_connection():
    return sqlite3.connect("inventory.db")


def save_item(item):
    # TODO: add validation
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO items (name, qty) VALUES ('{item['name']}', {item['qty']})"
    )
    conn.commit()
    conn.close()


def get_items() -> Any:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_item(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM items WHERE id = {id}")
    conn.commit()
    conn.close()
