#!/usr/bin/env python3

#########################################################
## HamSearch DB Downloader / Builder
## v.3.0 ALPHA
#########################################################

import os
import sqlite3
import zipfile
from datetime import datetime

import requests

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ZIP_PATH = os.path.join(BASE_DIR, "l_amat.zip")
DB_PATH = os.path.join(DATA_DIR, "hamsearch.db")
LOG_PATH = os.path.join(BASE_DIR, "hamsearch.log")

FCC_ZIP_URL = "https://data.fcc.gov/download/pub/uls/complete/l_amat.zip"

FILES_TO_EXTRACT = [
    "AM.dat",
    "EN.dat",
    "HD.dat",
    "HS.dat",
]

# -------------------------------------------------------
# LOGGING
# -------------------------------------------------------

def log_it(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} {message}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")

# -------------------------------------------------------
# FILE / DIR HELPERS
# -------------------------------------------------------

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def download_zip():
    log_it("Downloading FCC amateur license ZIP file")
    response = requests.get(FCC_ZIP_URL, timeout=120)
    response.raise_for_status()

    with open(ZIP_PATH, "wb") as handle:
        handle.write(response.content)

    log_it(f"Downloaded ZIP to {ZIP_PATH}")

def extract_zip():
    log_it("Extracting FCC data files")
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        available = set(archive.namelist())

        for filename in FILES_TO_EXTRACT:
            if filename in available:
                archive.extract(filename, DATA_DIR)
                log_it(f"Extracted {filename}")
            else:
                log_it(f"WARNING: {filename} not found in ZIP")

# -------------------------------------------------------
# SQLITE SCHEMA
# -------------------------------------------------------

def create_schema(conn):
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        DROP TABLE IF EXISTS meta;
        DROP TABLE IF EXISTS entities;
        DROP TABLE IF EXISTS amateur;
        DROP TABLE IF EXISTS licenses;
        DROP TABLE IF EXISTS history_status;
        DROP TABLE IF EXISTS raw_records;

        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE entities (
            unique_system_identifier TEXT PRIMARY KEY,
            callsign TEXT,
            entity_name TEXT,
            first_name TEXT,
            mi TEXT,
            last_name TEXT,
            suffix TEXT,
            street_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            raw_line TEXT
        );

        CREATE TABLE amateur (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_system_identifier TEXT,
            callsign TEXT,
            operator_class TEXT,
            group_code TEXT,
            region_code TEXT,
            trustee_callsign TEXT,
            previous_callsign TEXT,
            previous_operator_class TEXT,
            raw_line TEXT
        );

        CREATE TABLE licenses (
            unique_system_identifier TEXT PRIMARY KEY,
            callsign TEXT,
            license_status TEXT,
            radio_service_code TEXT,
            grant_date TEXT,
            expired_date TEXT,
            cancellation_date TEXT,
            raw_line TEXT
        );

        CREATE TABLE history_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_system_identifier TEXT,
            callsign TEXT,
            log_date TEXT,
            status_code TEXT,
            status_text TEXT,
            raw_line TEXT
        );

        CREATE TABLE raw_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT,
            unique_system_identifier TEXT,
            callsign TEXT,
            raw_line TEXT
        );

        CREATE INDEX idx_entities_callsign ON entities(callsign);
        CREATE INDEX idx_amateur_callsign ON amateur(callsign);
        CREATE INDEX idx_amateur_prev_callsign ON amateur(previous_callsign);
        CREATE INDEX idx_licenses_callsign ON licenses(callsign);
        CREATE INDEX idx_history_callsign ON history_status(callsign);
        CREATE INDEX idx_history_usi ON history_status(unique_system_identifier);
        """
    )

# -------------------------------------------------------
# PARSERS
# -------------------------------------------------------

def clean(value):
    return (value or "").strip()

def get_field(parts, index):
    if index < len(parts):
        return clean(parts[index])
    return ""

def parse_en_line(parts):
    # Based on the fields already used in your repo:
    # callsign at [4]
    # name parts at [8]-[11]
    # address at [15]-[18]
    return {
        "unique_system_identifier": get_field(parts, 1),
        "callsign": get_field(parts, 4).upper(),
        "entity_name": get_field(parts, 7),
        "first_name": get_field(parts, 8),
        "mi": get_field(parts, 9),
        "last_name": get_field(parts, 10),
        "suffix": get_field(parts, 11),
        "street_address": get_field(parts, 15),
        "city": get_field(parts, 16),
        "state": get_field(parts, 17),
        "zip_code": get_field(parts, 18),
    }

def parse_am_line(parts):
    # Based on the fields already used in your repo:
    # callsign at [4]
    # operator class at [5]
    # previous callsign/class at [15]/[16]
    return {
        "unique_system_identifier": get_field(parts, 1),
        "callsign": get_field(parts, 4).upper(),
        "operator_class": get_field(parts, 5),
        "group_code": get_field(parts, 6),
        "region_code": get_field(parts, 7),
        "trustee_callsign": get_field(parts, 14).upper(),
        "previous_callsign": get_field(parts, 15).upper(),
        "previous_operator_class": get_field(parts, 16),
    }

def parse_hd_line(parts):
    # FCC public-access record definitions show HD includes:
    # unique system identifier, callsign, license status,
    # radio service code, grant date, expired date, cancellation date.
    return {
        "unique_system_identifier": get_field(parts, 1),
        "callsign": get_field(parts, 4).upper(),
        "license_status": get_field(parts, 5),
        "radio_service_code": get_field(parts, 6),
        "grant_date": get_field(parts, 7),
        "expired_date": get_field(parts, 8),
        "cancellation_date": get_field(parts, 9),
    }

def parse_hs_line(parts):
    # FCC definitions show HS is history/status-oriented.
    # We preserve raw_line too, in case FCC changes field details again.
    return {
        "unique_system_identifier": get_field(parts, 1),
        "callsign": get_field(parts, 3).upper(),
        "log_date": get_field(parts, 4),
        "status_code": get_field(parts, 5),
        "status_text": get_field(parts, 6),
    }

# -------------------------------------------------------
# IMPORTERS
# -------------------------------------------------------

def import_en(conn, filepath):
    if not os.path.exists(filepath):
        log_it("EN.dat missing, skipping")
        return 0

    count = 0
    with open(filepath, "r", encoding="latin-1", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue

            parts = line.split("|")
            rec = parse_en_line(parts)
            raw_usi = rec["unique_system_identifier"]
            raw_callsign = rec["callsign"]

            conn.execute(
                """
                INSERT OR REPLACE INTO entities (
                    unique_system_identifier,
                    callsign,
                    entity_name,
                    first_name,
                    mi,
                    last_name,
                    suffix,
                    street_address,
                    city,
                    state,
                    zip_code,
                    raw_line
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_usi,
                    raw_callsign,
                    rec["entity_name"],
                    rec["first_name"],
                    rec["mi"],
                    rec["last_name"],
                    rec["suffix"],
                    rec["street_address"],
                    rec["city"],
                    rec["state"],
                    rec["zip_code"],
                    line,
                ),
            )

            conn.execute(
                """
                INSERT INTO raw_records (record_type, unique_system_identifier, callsign, raw_line)
                VALUES (?, ?, ?, ?)
                """,
                ("EN", raw_usi, raw_callsign, line),
            )

            count += 1

    log_it(f"Imported EN.dat rows: {count}")
    return count

def import_am(conn, filepath):
    if not os.path.exists(filepath):
        log_it("AM.dat missing, skipping")
        return 0

    count = 0
    with open(filepath, "r", encoding="latin-1", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue

            parts = line.split("|")
            rec = parse_am_line(parts)
            raw_usi = rec["unique_system_identifier"]
            raw_callsign = rec["callsign"]

            conn.execute(
                """
                INSERT INTO amateur (
                    unique_system_identifier,
                    callsign,
                    operator_class,
                    group_code,
                    region_code,
                    trustee_callsign,
                    previous_callsign,
                    previous_operator_class,
                    raw_line
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_usi,
                    raw_callsign,
                    rec["operator_class"],
                    rec["group_code"],
                    rec["region_code"],
                    rec["trustee_callsign"],
                    rec["previous_callsign"],
                    rec["previous_operator_class"],
                    line,
                ),
            )

            conn.execute(
                """
                INSERT INTO raw_records (record_type, unique_system_identifier, callsign, raw_line)
                VALUES (?, ?, ?, ?)
                """,
                ("AM", raw_usi, raw_callsign, line),
            )

            count += 1

    log_it(f"Imported AM.dat rows: {count}")
    return count

def import_hd(conn, filepath):
    if not os.path.exists(filepath):
        log_it("HD.dat missing, skipping")
        return 0

    count = 0
    with open(filepath, "r", encoding="latin-1", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue

            parts = line.split("|")
            rec = parse_hd_line(parts)
            raw_usi = rec["unique_system_identifier"]
            raw_callsign = rec["callsign"]

            conn.execute(
                """
                INSERT OR REPLACE INTO licenses (
                    unique_system_identifier,
                    callsign,
                    license_status,
                    radio_service_code,
                    grant_date,
                    expired_date,
                    cancellation_date,
                    raw_line
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_usi,
                    raw_callsign,
                    rec["license_status"],
                    rec["radio_service_code"],
                    rec["grant_date"],
                    rec["expired_date"],
                    rec["cancellation_date"],
                    line,
                ),
            )

            conn.execute(
                """
                INSERT INTO raw_records (record_type, unique_system_identifier, callsign, raw_line)
                VALUES (?, ?, ?, ?)
                """,
                ("HD", raw_usi, raw_callsign, line),
            )

            count += 1

    log_it(f"Imported HD.dat rows: {count}")
    return count

def import_hs(conn, filepath):
    if not os.path.exists(filepath):
        log_it("HS.dat missing, skipping")
        return 0

    count = 0
    with open(filepath, "r", encoding="latin-1", errors="ignore") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue

            parts = line.split("|")
            rec = parse_hs_line(parts)
            raw_usi = rec["unique_system_identifier"]
            raw_callsign = rec["callsign"]

            conn.execute(
                """
                INSERT INTO history_status (
                    unique_system_identifier,
                    callsign,
                    log_date,
                    status_code,
                    status_text,
                    raw_line
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_usi,
                    raw_callsign,
                    rec["log_date"],
                    rec["status_code"],
                    rec["status_text"],
                    line,
                ),
            )

            conn.execute(
                """
                INSERT INTO raw_records (record_type, unique_system_identifier, callsign, raw_line)
                VALUES (?, ?, ?, ?)
                """,
                ("HS", raw_usi, raw_callsign, line),
            )

            count += 1

    log_it(f"Imported HS.dat rows: {count}")
    return count

# -------------------------------------------------------
# BUILD SQLITE
# -------------------------------------------------------

def build_sqlite_db():
    log_it("Building SQLite database")

    conn = sqlite3.connect(DB_PATH)

    try:
        create_schema(conn)

        import_en(conn, os.path.join(DATA_DIR, "EN.dat"))
        import_am(conn, os.path.join(DATA_DIR, "AM.dat"))
        import_hd(conn, os.path.join(DATA_DIR, "HD.dat"))
        import_hs(conn, os.path.join(DATA_DIR, "HS.dat"))

        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("fcc_zip_url", FCC_ZIP_URL),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_build_utc", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")),
        )

        conn.commit()
        log_it(f"SQLite build complete: {DB_PATH}")

    finally:
        conn.close()

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main():
    ensure_dirs()
    download_zip()
    extract_zip()
    build_sqlite_db()
    log_it("Get DB process complete!")

if __name__ == "__main__":
    main()
