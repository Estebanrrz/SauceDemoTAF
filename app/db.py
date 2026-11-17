# SQLite database of the local shop (Python's built-in sqlite3, plain SQL, no ORM).
#
# Where the file is:
#   python app/server.py           SHOP_DB if set, otherwise app/shop.db (kept between runs, git-ignored)
#   the test suite starts the app  SHOP_DB if set, otherwise a new temporary file for that run only
#
# Every time the app starts, the tables are created if missing and users and products are copied from
# Data/users.json and Data/products.json, the same files the tests read: those files stay the single
# source of truth. Open the file with any SQLite viewer (e.g. DB Browser for SQLite) to look inside.
#
# Conventions:
#   prices are whole cents (price_cents 2999 = $29.99), so sums and tax have no float rounding errors
#   passwords and API tokens are stored only as hashes, never as plain text

import contextlib
import hashlib
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sqlite3
import threading

from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT_DIR, 'Data')
DEFAULT_DB_PATH = os.path.join(ROOT_DIR, 'app', 'shop.db')

# PBKDF2 with a low cost on purpose (about 80 ms per check): this is a local test app and the suites log
# in hundreds of times. A real shop would use the slower defaults.
PASSWORD_HASH_METHOD = 'pbkdf2:sha256:100000'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    locked        INTEGER NOT NULL DEFAULT 0 CHECK (locked IN (0, 1))
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,             -- 1, 2, 3... in the order of Data/products.json
    slug        TEXT NOT NULL UNIQUE,            -- sauce-labs-backpack (used in the page ids)
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);

CREATE TABLE IF NOT EXISTS api_tokens (
    token_hash TEXT PRIMARY KEY,                 -- SHA-256 of the Bearer token, never the token itself
    username   TEXT NOT NULL REFERENCES users (username),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    expires_at TEXT NOT NULL                     -- UTC, e.g. 2026-11-16T20:10:15.123Z (see utc_timestamp)
);

-- One cart per login (per token), like one cart per browser session on the web pages: two users, or the
-- same user logged in twice, never share a cart. Logout deletes the token and, with it, its cart.
-- Orders belong to the user (not to the token): an order placed today is still the user's after a new
-- login. Name and price are copied into order_items on purpose: the order keeps what was bought at the
-- price of that day, even if the catalog changes later.
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY,
    username       TEXT NOT NULL REFERENCES users (username),
    reference      TEXT NOT NULL UNIQUE,        -- sent to the payment service, ties order and charge
    card           TEXT NOT NULL,
    payment_id     TEXT NOT NULL,               -- given by the payment service
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    postal_code    TEXT NOT NULL,
    subtotal_cents INTEGER NOT NULL,
    tax_cents      INTEGER NOT NULL,
    total_cents    INTEGER NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products (id),
    name        TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    id         INTEGER PRIMARY KEY,              -- grows with every add: the cart keeps the order of adding
    token_hash TEXT NOT NULL REFERENCES api_tokens (token_hash) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products (id),
    UNIQUE (token_hash, product_id)              -- quantity is always 1
);
'''

_init_lock = threading.Lock()


def default_path():
    return os.environ.get('SHOP_DB') or DEFAULT_DB_PATH


def load_json(name):
    with open(os.path.join(DATA_DIR, name), encoding='utf-8') as f:
        return json.load(f)


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def product_description(name):
    return f'carry.allTheThings() with the {name}.'


def connect(path):
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row  # rows can be read by column name: row['price_cents']
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db(app, path):
    """Create the tables if needed, copy users and products from Data/*.json and use that file from now on."""
    with _init_lock, contextlib.closing(connect(path)) as connection:
        connection.execute('PRAGMA journal_mode = WAL')  # readers do not wait for writers (parallel runs)
        connection.executescript(SCHEMA)
        _migrate(connection)
        _seed(connection)
        connection.commit()
        app.config['SHOP_DB'] = path


def _migrate(connection):
    """Bring a database file made by an older version of the app up to date (CREATE TABLE IF NOT EXISTS
    does not add columns to a table that already exists)."""
    columns = {row['name'] for row in connection.execute('PRAGMA table_info(api_tokens)')}
    if 'expires_at' not in columns:
        # Tokens from before expiry existed get NULL, and the API treats NULL as expired: log in again
        connection.execute('ALTER TABLE api_tokens ADD COLUMN expires_at TEXT')


def utc_timestamp(seconds_from_now=0):
    """UTC time as text with milliseconds, e.g. '2026-11-16T20:10:15.123Z'. Always the same length and
    format, so two of them compare correctly as plain text (also in SQL)."""
    moment = datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)
    return moment.strftime('%Y-%m-%dT%H:%M:%S.') + f'{moment.microsecond // 1000:03d}Z'


def _seed(connection):
    """Make users and products match Data/*.json. Existing rows are updated, ids never change."""
    for username, info in load_json('users.json').items():
        connection.execute(
            'INSERT INTO users (username, password_hash, locked) VALUES (?, ?, ?) '
            'ON CONFLICT (username) DO UPDATE SET password_hash = excluded.password_hash, locked = excluded.locked',
            (username, generate_password_hash(info['password'], method=PASSWORD_HASH_METHOD),
             int(bool(info.get('locked', False)))))
    for product in load_json('products.json'):
        connection.execute(
            'INSERT INTO products (slug, name, description, price_cents) VALUES (?, ?, ?, ?) '
            'ON CONFLICT (slug) DO UPDATE SET name = excluded.name, description = excluded.description, '
            'price_cents = excluded.price_cents',
            (slugify(product['name']), product['name'], product_description(product['name']),
             round(product['price'] * 100)))


def get_db():
    """The connection of the current request (one per request, closed by close_db when it ends)."""
    if 'db' not in g:
        if 'SHOP_DB' not in current_app.config:  # started some other way, e.g. "flask --app app.server run"
            init_db(current_app, default_path())
        g.db = connect(current_app.config['SHOP_DB'])
    return g.db


def close_db(error=None):
    connection = g.pop('db', None)
    if connection is not None:
        connection.close()


def password_matches(user_row, password):
    return check_password_hash(user_row['password_hash'], password)


def token_hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
