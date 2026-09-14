"""Export an aggregate demo snapshot without starting or writing to the application.

Usage: python -B build_snapshot.py [--at 2026-09-12T16:20:00+05:00]
Only data.json beside this script is written. Source SQLite is opened mode=ro.
KPI definitions follow app/services/kpi.py; regional issued items must have
both their current cabinet and an open custody cabinet in the same region.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, time, timedelta, timezone
from pathlib import Path


LOCAL_TZ = timezone(timedelta(hours=5))
DIRECTORY = Path(__file__).resolve().parent
DEFAULT_DB = DIRECTORY.parents[2] / "admin-panel" / "data" / "aq_central.sqlite3"
OPS = ("avtomat_olindi", "avtomat_qaytarildi", "pm_olindi", "pm_qaytarildi")


def iso_local(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TZ)
    return parsed.astimezone(LOCAL_TZ).isoformat(timespec="seconds")


def export_snapshot(source: Path, captured_at: datetime) -> dict:
    # The application stores naive timestamps in local Tashkent time.
    now = captured_at.astimezone(LOCAL_TZ).replace(tzinfo=None)
    now_sql = now.isoformat(sep=" ", timespec="microseconds")
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        # A consistent read transaction includes every aggregation below.
        db.execute("BEGIN")

        def scalar(sql: str, params: tuple = ()) -> int:
            return db.execute(sql, params).fetchone()[0] or 0

        def custody_count(region_id: int | None = None, overdue: bool = False) -> int:
            sql = """SELECT COUNT(DISTINCT i.id) FROM item i
                     WHERE i.kind = 'qurol' AND EXISTS (
                         SELECT 1 FROM custody c
                         WHERE c.item_id = i.id AND c.returned_at IS NULL"""
            params: list = []
            if overdue:
                sql += " AND c.due_at < ?"
                params.append(now_sql)
            if region_id is not None:
                sql += """ AND c.cabinet_id IN (
                    SELECT cb.id FROM cabinet cb JOIN armory a ON a.id = cb.armory_id
                    JOIN unit u ON u.id = a.unit_id WHERE u.region_id = ?)"""
                params.append(region_id)
            sql += ")"
            if region_id is not None:
                sql += """ AND i.cabinet_id IN (
                    SELECT cb.id FROM cabinet cb JOIN armory a ON a.id = cb.armory_id
                    JOIN unit u ON u.id = a.unit_id WHERE u.region_id = ?)"""
                params.append(region_id)
            return scalar(sql, tuple(params))

        def alarm_counts(region_id: int | None = None) -> dict:
            where = "resolved_at IS NULL"
            params = ()
            if region_id is not None:
                where += " AND region_id = ?"
                params = (region_id,)
            row = db.execute(f"""SELECT COUNT(*) AS active_alarms,
                COALESCE(SUM(level IN ('CRITICAL', 'SECURITY')), 0) AS serious_alarms,
                COALESCE(SUM(level = 'WARNING'), 0) AS warnings,
                COALESCE(SUM(requires_ack = 1 AND acked_at IS NULL), 0) AS pending_ack
                FROM alarm WHERE {where}""", params).fetchone()
            return dict(row)

        regions = []
        for region in db.execute('SELECT id, code, short FROM region ORDER BY "order", id'):
            region_id = region["id"]
            armories = scalar("""SELECT COUNT(*) FROM armory a
                JOIN unit u ON u.id = a.unit_id WHERE u.region_id = ?""", (region_id,))
            offline = scalar("""SELECT COUNT(*) FROM armory a
                JOIN unit u ON u.id = a.unit_id WHERE u.region_id = ? AND a.online = 0""", (region_id,))
            alarms = alarm_counts(region_id)
            regions.append({
                "id": region_id, "code": region["code"], "name": region["short"],
                "armories": armories,
                "cabinets": scalar("""SELECT COUNT(*) FROM cabinet cb
                    JOIN armory a ON a.id = cb.armory_id JOIN unit u ON u.id = a.unit_id
                    WHERE u.region_id = ?""", (region_id,)),
                "issued": custody_count(region_id), "overdue": custody_count(region_id, True),
                "active_alarms": alarms["active_alarms"],
                "serious_alarms": alarms["serious_alarms"], "warnings": alarms["warnings"],
                "offline": offline, "online": armories - offline,
            })

        armories = scalar("SELECT COUNT(*) FROM armory")
        offline = scalar("SELECT COUNT(*) FROM armory WHERE online = 0")
        summary = {
            "regions": scalar("SELECT COUNT(*) FROM region"), "armories": armories,
            "cabinets": scalar("SELECT COUNT(*) FROM cabinet"),
            "weapons": scalar("SELECT COUNT(*) FROM item WHERE kind = 'qurol'"),
            "issued": custody_count(), "overdue": custody_count(overdue=True),
            "open_records": scalar("""SELECT COUNT(*) FROM custody c JOIN item i ON i.id = c.item_id
                WHERE c.returned_at IS NULL AND i.kind = 'qurol'"""),
            **alarm_counts(), "online": armories - offline, "offline": offline,
            "attention_regions": sum(bool(r["active_alarms"] or r["offline"]) for r in regions),
        }

        days = []
        weekday_names = ("Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya")
        for days_ago in range(6, -1, -1):
            day = now.date() - timedelta(days=days_ago)
            start = datetime.combine(day, time.min)
            end = start + timedelta(days=1)
            count = scalar("""SELECT COUNT(*) FROM event WHERE ts_server >= ? AND ts_server < ?
                AND type IN (?, ?, ?, ?)""", (start.isoformat(sep=" "), end.isoformat(sep=" "), *OPS))
            days.append({"date": day.isoformat(), "label": weekday_names[day.weekday()],
                         "value": count, "today": days_ago == 0})

        latest_event = db.execute("SELECT MAX(ts_server) FROM event").fetchone()[0]
        oldest_sync, newest_sync = db.execute("SELECT MIN(last_sync), MAX(last_sync) FROM armory").fetchone()
        simulated = scalar("SELECT COUNT(*) FROM event WHERE simulated = 1")
        total_events = scalar("SELECT COUNT(*) FROM event")
        duplicate_records = summary["open_records"] - summary["issued"]
        notes = [
            f"Demo ma’lumotlari: {total_events:,} hodisadan {simulated:,} tasi simulyatsiya sifatida belgilangan.".replace(",", " "),
            "Bu jonli kuzatuv emas; ko‘rsatkichlar mahalliy bazaning o‘qish orqali olingan holat nusxasidir.",
            f"{summary['issued']} ta alohida qurolga {summary['open_records']} ta ochiq berish qaydi tegishli; "
            f"{duplicate_records} ta ortiqcha takroriy qayd bor. Tarixiy qaydlar o‘zgartirilmagan.",
            "Aloqa holati va berilmagan qurollar hisobi tayyorlik yoki foydalanishga ruxsatni tasdiqlamaydi.",
            "Faol signallar barcha hal qilinmagan qaydlarni; jiddiy signallar CRITICAL va SECURITY darajalarini hisoblaydi.",
            "Haftalik operatsiyalar faqat bazadagi olish va qaytarish hodisalaridan hisoblangan; bugungi kun hali tugamagan. "
            "0 qiymat shu kuni bazada qayd yo‘qligini bildiradi.",
        ]
        output = {
            "captured_at": captured_at.astimezone(LOCAL_TZ).isoformat(timespec="seconds"),
            "source_label": "Mahalliy demo bazasi", "source_latest_event": iso_local(latest_event),
            "armory_sync": {"oldest": iso_local(oldest_sync), "newest": iso_local(newest_sync)},
            "summary": summary, "regions": regions, "daily_ops": days, "notes": notes,
        }
        validate(output)
        return output


def validate(data: dict) -> None:
    summary, regions = data["summary"], data["regions"]
    if len(regions) != summary["regions"]:
        raise ValueError("Region count differs from aggregate")
    for key in ("armories", "cabinets", "issued", "overdue", "active_alarms", "serious_alarms", "warnings", "online", "offline"):
        if sum(row[key] for row in regions) != summary[key]:
            raise ValueError(f"Regional aggregate mismatch: {key}")
    if summary["online"] + summary["offline"] != summary["armories"]:
        raise ValueError("Armory connection aggregate mismatch")
    if not 0 <= summary["overdue"] <= summary["issued"] <= summary["open_records"]:
        raise ValueError("Invalid open-custody counts")
    if summary["serious_alarms"] + summary["warnings"] > summary["active_alarms"]:
        raise ValueError("Alarm severity aggregate mismatch")
    if len(data["daily_ops"]) != 7 or sum(row["today"] for row in data["daily_ops"]) != 1:
        raise ValueError("Invalid seven-day operation series")
    if any(value < 0 for value in summary.values()):
        raise ValueError("Negative aggregate count")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Read-only source SQLite file")
    parser.add_argument("--at", help="ISO reference time for reproducible current-state counts; this does not reconstruct past database state")
    args = parser.parse_args()
    captured_at = datetime.fromisoformat(args.at) if args.at else datetime.now(LOCAL_TZ)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=LOCAL_TZ)
    data = export_snapshot(args.db, captured_at)
    destination = DIRECTORY / "data.json"
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = data["summary"]
    print(f"Snapshot validated: {s['regions']} regions, {s['armories']} armories, {s['cabinets']} cabinets; "
          f"{s['active_alarms']} active / {s['serious_alarms']} serious alarms; "
          f"{s['issued']} distinct issued / {s['open_records']} open records; 7 daily totals. Wrote data.json.")


if __name__ == "__main__":
    main()
