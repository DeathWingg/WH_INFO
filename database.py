import sqlite3
from contextlib import contextmanager

from config import DB_PATH

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS manufacturers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    manufacturer_id INTEGER,
    model TEXT,
    category TEXT DEFAULT 'Celular',
    description TEXT,
    processor TEXT,
    ram TEXT,
    storage TEXT,
    screen_size TEXT,
    resolution TEXT,
    cameras TEXT,
    battery TEXT,
    os TEXT,
    connectivity TEXT,
    warranty TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
);

CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    color TEXT,
    filename TEXT NOT NULL,
    is_primary INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS variations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    storage TEXT,
    color TEXT,
    supplier_cost REAL NOT NULL DEFAULT 0,
    stock INTEGER NOT NULL DEFAULT 0,
    sku TEXT,
    active INTEGER DEFAULT 1,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    cpf TEXT,
    email TEXT
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_number TEXT UNIQUE,
    client_id INTEGER,
    client_name TEXT,
    payment_method TEXT NOT NULL,
    installments INTEGER NOT NULL DEFAULT 1,
    total REAL NOT NULL,
    profit REAL NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    variation_id INTEGER,
    product_name TEXT,
    storage TEXT,
    color TEXT,
    unit_price REAL,
    unit_cost REAL,
    quantity INTEGER,
    image_filename TEXT,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variation_id INTEGER NOT NULL,
    delta INTEGER NOT NULL,
    reason TEXT,
    sale_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variation_id) REFERENCES variations(id)
);

CREATE TABLE IF NOT EXISTS payment_fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT NOT NULL,
    installments INTEGER NOT NULL DEFAULT 1,
    fee_percent REAL NOT NULL DEFAULT 0,
    fixed_fee REAL NOT NULL DEFAULT 0,
    UNIQUE(method, installments)
);

CREATE INDEX IF NOT EXISTS idx_var_product ON variations(product_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at);
"""

DEFAULT_SETTINGS = {
    "store_name": "WH INFO",
    "store_subtitle": "Sistema de Gerenciamento e Vendas",
    "store_phone": "",
    "store_address": "",
    "store_email": "",
    "margin_cash": "20",
    "margin_debit": "22",
    "margin_credit": "25",
    "margin_mode": "markup_on_cost",
    "low_stock_threshold": "3",
    "allow_backorder": "0",
    "admin_password_hash": "",
}

DEFAULT_FEES = [
    ("cash", 1, 0.0, 0.0),
    ("debit", 1, 1.99, 0.0),
    ("credit", 1, 3.99, 0.0),
    ("credit", 2, 5.99, 0.0),
    ("credit", 3, 6.99, 0.0),
    ("credit", 4, 8.49, 0.0),
    ("credit", 5, 9.49, 0.0),
    ("credit", 6, 10.99, 0.0),
    ("credit", 10, 14.99, 0.0),
    ("credit", 12, 17.99, 0.0),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    from werkzeug.security import generate_password_hash

    with db() as conn:
        conn.executescript(SCHEMA)
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        row = conn.execute(
            "SELECT value FROM settings WHERE key='admin_password_hash'"
        ).fetchone()
        if not row or not row["value"]:
            conn.execute(
                "UPDATE settings SET value=? WHERE key='admin_password_hash'",
                (generate_password_hash("admin123"),),
            )
        for method, inst, pct, fixed in DEFAULT_FEES:
            conn.execute(
                "INSERT OR IGNORE INTO payment_fees (method, installments, fee_percent, fixed_fee) "
                "VALUES (?, ?, ?, ?)",
                (method, inst, pct, fixed),
            )
