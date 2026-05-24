"""
db.py — Conexión y operaciones de base de datos
Soporta PostgreSQL (producción) y SQLite (desarrollo local)
"""

import os
import sqlite3
from datetime import datetime

# ─────────────────────────────────────────────
# Detectar qué BD usar
# ─────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgresql")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect("prices.db")

# ─────────────────────────────────────────────
# Inicializar BD
# ─────────────────────────────────────────────
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                store TEXT NOT NULL,
                product_url TEXT NOT NULL,
                product_name TEXT,
                price INTEGER,
                timestamp TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                product_url TEXT NOT NULL,
                product_name TEXT,
                price INTEGER,
                timestamp TEXT NOT NULL
            )
        """)
    conn.commit()
    return conn

# ─────────────────────────────────────────────
# Operaciones
# ─────────────────────────────────────────────
def save_price(conn, store, url, name, price):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO price_history (store, product_url, product_name, price, timestamp) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES
        else "INSERT INTO price_history (store, product_url, product_name, price, timestamp) VALUES (?,?,?,?,?)",
        (store, url, name, price, datetime.now().isoformat())
    )
    conn.commit()

def get_last_price(conn, url):
    cur = conn.cursor()
    q = "SELECT price FROM price_history WHERE product_url=%s ORDER BY timestamp DESC LIMIT 1" if USE_POSTGRES \
        else "SELECT price FROM price_history WHERE product_url=? ORDER BY timestamp DESC LIMIT 1"
    cur.execute(q, (url,))
    row = cur.fetchone()
    return row[0] if row else None

def get_last_date(conn, url):
    cur = conn.cursor()
    q = "SELECT timestamp FROM price_history WHERE product_url=%s ORDER BY timestamp DESC LIMIT 1" if USE_POSTGRES \
        else "SELECT timestamp FROM price_history WHERE product_url=? ORDER BY timestamp DESC LIMIT 1"
    cur.execute(q, (url,))
    row = cur.fetchone()
    return row[0][:10] if row else None

def get_max_price(conn, url):
    cur = conn.cursor()
    q = "SELECT MAX(price) FROM price_history WHERE product_url=%s" if USE_POSTGRES \
        else "SELECT MAX(price) FROM price_history WHERE product_url=?"
    cur.execute(q, (url,))
    row = cur.fetchone()
    return row[0] if row and row[0] else None

def get_all_history():
    """Para el dashboard — devuelve todo el historial como lista de dicts."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT store, product_url, product_name, price, timestamp
        FROM price_history
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {"store": r[0], "product_url": r[1], "product_name": r[2], "price": r[3], "timestamp": r[4]}
        for r in rows
    ]
