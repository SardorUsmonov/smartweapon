"""Read-only check that every baseline row survives an additive update."""
import argparse
import sqlite3
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("baseline", type=Path)
parser.add_argument("current", type=Path)
args = parser.parse_args()


def read_only(path):
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def identifier(name):
    return '"' + name.replace('"', '""') + '"'


failures = []
with read_only(args.baseline) as baseline, read_only(args.current) as current:
    tables = baseline.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    for (table,) in tables:
        columns = [row[1] for row in baseline.execute(f"PRAGMA table_info({identifier(table)})")]
        query = "SELECT " + ", ".join(map(identifier, columns)) + " FROM " + identifier(table)
        old = Counter(baseline.execute(query).fetchall())
        new = Counter(current.execute(query).fetchall())
        missing = sum((old - new).values())
        print(f"{table}: baseline={sum(old.values())}, current={sum(new.values())}, changed_or_missing={missing}")
        if missing:
            failures.append(table)
if failures:
    raise SystemExit("Preservation failed: " + ", ".join(failures))
print("PASS: every original row is present unchanged; additive rows/tables are allowed.")
