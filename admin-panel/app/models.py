"""Ma'lumotlar modeli (02-talablar §3 bo'yicha). Atamalar: yacheyka = bir xodimning shkafi."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# ---------------- Ierarxiya ----------------
class Region(Base):
    __tablename__ = "region"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)      # UZ-TK
    name: Mapped[str] = mapped_column(String(80))                  # Toshkent shahri
    short: Mapped[str] = mapped_column(String(40))                 # Toshkent sh.
    order: Mapped[int] = mapped_column(Integer, default=0)
    units: Mapped[list["Unit"]] = relationship(back_populates="region")


class Unit(Base):
    """Tuman/shahar IIB yoki funksional bo'linma."""
    __tablename__ = "unit"
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("region.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40), default="tuman_iib")  # tuman_iib | shahar_iib | funksional
    region: Mapped["Region"] = relationship(back_populates="units")
    armories: Mapped[list["Armory"]] = relationship(back_populates="unit")


class Armory(Base):
    """Qurolxona: lokal kontroller (role=armory) darajasi."""
    __tablename__ = "armory"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(200), default="")
    online: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    wan_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    ups_on_battery: Mapped[bool] = mapped_column(Boolean, default=False)
    ups_battery_pct: Mapped[int] = mapped_column(Integer, default=100)
    pending_events: Mapped[int] = mapped_column(Integer, default=0)
    responsible_officer_id: Mapped[int | None] = mapped_column(ForeignKey("officer.id"), nullable=True)
    approvers_required: Mapped[int] = mapped_column(Integer, default=2)
    unit: Mapped["Unit"] = relationship(back_populates="armories")
    cabinets: Mapped[list["Cabinet"]] = relationship(back_populates="armory", foreign_keys="Cabinet.armory_id")


class Cabinet(Base):
    """Yacheyka (bir xodimning shkafi)."""
    __tablename__ = "cabinet"
    id: Mapped[int] = mapped_column(primary_key=True)
    armory_id: Mapped[int] = mapped_column(ForeignKey("armory.id"), index=True)
    serial: Mapped[str] = mapped_column(String(40), unique=True)   # SHK-2026-000123
    label: Mapped[str] = mapped_column(String(20))                 # Y-017 (qurolxona ichida)
    wall: Mapped[str] = mapped_column(String(4), default="A")
    position: Mapped[int] = mapped_column(Integer, default=1)
    # hayot holati: zaxira | biriktirilgan | bloklangan | nosoz | xizmatda
    status: Mapped[str] = mapped_column(String(20), default="zaxira", index=True)
    officer_id: Mapped[int | None] = mapped_column(ForeignKey("officer.id"), nullable=True, index=True)
    # jonli telemetriya
    door_open: Mapped[bool] = mapped_column(Boolean, default=False)
    door_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    ak_present: Mapped[bool] = mapped_column(Boolean, default=True)
    pm_present: Mapped[bool] = mapped_column(Boolean, default=True)
    ak_clamp_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    pm_box_locked: Mapped[bool] = mapped_column(Boolean, default=True)
    mains_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    battery_pct: Mapped[int] = mapped_column(Integer, default=100)
    temp_c: Mapped[float] = mapped_column(Float, default=21.0)
    controller_online: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    terminal_state: Mapped[str] = mapped_column(String(20), default="idle")  # idle|face|finger|ok|open|lock|denied|blocked
    armory: Mapped["Armory"] = relationship(back_populates="cabinets", foreign_keys=[armory_id])
    officer: Mapped["Officer | None"] = relationship(foreign_keys=[officer_id], post_update=True)


# ---------------- Xodim va vakolat ----------------
class Officer(Base):
    __tablename__ = "officer"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), index=True)
    armory_id: Mapped[int | None] = mapped_column(ForeignKey("armory.id"), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    tabel: Mapped[str] = mapped_column(String(20), unique=True)
    position: Mapped[str] = mapped_column(String(80), default="Inspektor")
    rank: Mapped[str] = mapped_column(String(40), default="Leytenant")
    # faol | ta'tilda | kasallik | vaqtincha_chetlashtirilgan | ishdan_boshagan
    service_status: Mapped[str] = mapped_column(String(30), default="faol")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    card_uid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_status: Mapped[str] = mapped_column(String(16), default="faol")
    face_enrolled: Mapped[bool] = mapped_column(Boolean, default=True)
    finger_enrolled: Mapped[bool] = mapped_column(Boolean, default=True)
    permit_ak: Mapped[bool] = mapped_column(Boolean, default=True)
    permit_pm: Mapped[bool] = mapped_column(Boolean, default=True)
    eligibility: Mapped[list["Eligibility"]] = relationship(back_populates="officer")


class Eligibility(Base):
    """5 shart [01 §2.2]: qurol biriktirilgan, vakolat, tayyorgarlik, yaroqlilik tekshiruvi, rahbar buyrug'i."""
    __tablename__ = "eligibility"
    id: Mapped[int] = mapped_column(primary_key=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("officer.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    doc_ref: Mapped[str] = mapped_column(String(80), default="")
    issued: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    officer: Mapped["Officer"] = relationship(back_populates="eligibility")


class Shift(Base):
    """Xizmat navbati (smena oynasi)."""
    __tablename__ = "shift"
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("officer.id"), index=True)
    start: Mapped[datetime] = mapped_column(DateTime)
    end: Mapped[datetime] = mapped_column(DateTime)
    confirmed_by: Mapped[str] = mapped_column(String(80), default="")


# ---------------- Inventar ----------------
class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)      # qurol | magazin | oq_dori | jihoz
    category: Mapped[str] = mapped_column(String(40))              # avtomat | to'pponcha | dubulg'a | ...
    model: Mapped[str] = mapped_column(String(40), default="")     # AK-74, PM, 6B47
    serial: Mapped[str] = mapped_column(String(40), index=True)
    rfid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinet.id"), nullable=True, index=True)
    officer_id: Mapped[int | None] = mapped_column(ForeignKey("officer.id"), nullable=True, index=True)
    slot: Mapped[str] = mapped_column(String(30), default="")
    qty: Mapped[int] = mapped_column(Integer, default=1)
    # mavjud | yo'q (xodimda) | nosoz | xizmatda
    state: Mapped[str] = mapped_column(String(20), default="mavjud", index=True)
    inspection_state: Mapped[str] = mapped_column(String(30), default="yaroqli")  # yaroqli | ko'rik_kutilmoqda | ko'rikda | ta'mirda
    next_inspection: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hold: Mapped[bool] = mapped_column(Boolean, default=False)


class Custody(Base):
    """Olish-qaytarish (chain of custody)."""
    __tablename__ = "custody"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("officer.id"), index=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinet.id"), index=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    match_ok: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------- Hodisalar va signallar ----------------
class Event(Base):
    """Append-only jurnal, hash zanjiri bilan (02 §3.5)."""
    __tablename__ = "event"
    id: Mapped[int] = mapped_column(primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)            # kontroller tartib raqami (yacheyka oqimi bo'yicha)
    ts_device: Mapped[datetime] = mapped_column(DateTime, index=True)
    ts_server: Mapped[datetime] = mapped_column(DateTime, index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    level: Mapped[str] = mapped_column(String(10), default="INFO", index=True)   # INFO|WARNING|CRITICAL|SECURITY
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"), nullable=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("unit.id"), nullable=True, index=True)
    armory_id: Mapped[int | None] = mapped_column(ForeignKey("armory.id"), nullable=True, index=True)
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinet.id"), nullable=True, index=True)
    officer_id: Mapped[int | None] = mapped_column(ForeignKey("officer.id"), nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(30), default="")     # KARTA+BARMOQ, YUZ+BARMOQ, PIN, FAVQULODDA, MEXANIK
    result: Mapped[str] = mapped_column(String(20), default="ok")
    reason: Mapped[str] = mapped_column(String(60), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    approver1: Mapped[str] = mapped_column(String(80), default="")
    approver2: Mapped[str] = mapped_column(String(80), default="")
    offline: Mapped[bool] = mapped_column(Boolean, default=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    detail: Mapped[str] = mapped_column(String(300), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), default="")
    hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    media_ref: Mapped[str] = mapped_column(String(120), default="")


Index("ix_event_ts_type", Event.ts_server, Event.type)


class Alarm(Base):
    __tablename__ = "alarm"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("event.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    region_id: Mapped[int | None] = mapped_column(ForeignKey("region.id"), nullable=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("unit.id"), nullable=True)
    armory_id: Mapped[int | None] = mapped_column(ForeignKey("armory.id"), nullable=True, index=True)
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinet.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    detail: Mapped[str] = mapped_column(String(300), default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    acked_by: Mapped[str] = mapped_column(String(80), default="")
    acked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str] = mapped_column(String(80), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    forwarded: Mapped[bool] = mapped_column(Boolean, default=False)   # qorovul postiga
    requires_ack: Mapped[bool] = mapped_column(Boolean, default=False)


class Mode(Base):
    """Yig'ilish / Trevoga rejimi."""
    __tablename__ = "mode"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))                   # yigilish | trevoga
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("unit.id"), nullable=True)
    armory_id: Mapped[int | None] = mapped_column(ForeignKey("armory.id"), nullable=True, index=True)
    started_by: Mapped[str] = mapped_column(String(80), default="")
    approver2: Mapped[str] = mapped_column(String(80), default="")
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    target_count: Mapped[int] = mapped_column(Integer, default=0)
    issued_count: Mapped[int] = mapped_column(Integer, default=0)
    queue_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_seconds: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(200), default="")


class ArmoryShift(Base):
    """Smena (obyekt darajasi, TZ §7.1, §7.4)."""
    __tablename__ = "armory_shift"
    id: Mapped[int] = mapped_column(primary_key=True)
    armory_id: Mapped[int] = mapped_column(ForeignKey("armory.id"), index=True)
    opened_by: Mapped[str] = mapped_column(String(80), default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    selfcheck: Mapped[dict] = mapped_column(JSON, default=dict)
    reconcile: Mapped[dict] = mapped_column(JSON, default=dict)
    permits_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_by: Mapped[str] = mapped_column(String(80), default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_confirm: Mapped[str] = mapped_column(String(80), default="")
    report_ref: Mapped[str] = mapped_column(String(120), default="")


class Device(Base):
    """Obyekt qurilmalari: kamera, kommutator, UPS, NAS, server, terminal."""
    __tablename__ = "device"
    id: Mapped[int] = mapped_column(primary_key=True)
    armory_id: Mapped[int] = mapped_column(ForeignKey("armory.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="onlayn")   # onlayn | oflayn | ogohlantirish
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Backup(Base):
    __tablename__ = "backup"
    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(40), default="markaz")
    kind: Mapped[str] = mapped_column(String(20))                   # kunlik | haftalik | tiklash_sinovi
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    size_mb: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(160), default="")


class User(Base):
    """Panel foydalanuvchisi (rol va vakolat doirasi)."""
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40))                   # tekshiruvchi | qurolxona_masuli | navbatchi | administrator | rahbariyat
    scope_kind: Mapped[str] = mapped_column(String(20), default="respublika")  # respublika | hudud | bolinma | qurolxona
    scope_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mfa: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ExportLog(Base):
    __tablename__ = "export_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(30))
    username: Mapped[str] = mapped_column(String(40))
    report: Mapped[str] = mapped_column(String(60))
    fmt: Mapped[str] = mapped_column(String(10))
    purpose: Mapped[str] = mapped_column(String(200), default="")
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    file_hash: Mapped[str] = mapped_column(String(64), default="")


class SettingsAudit(Base):
    __tablename__ = "settings_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40))
    key: Mapped[str] = mapped_column(String(80))
    old: Mapped[str] = mapped_column(Text, default="")
    new: Mapped[str] = mapped_column(Text, default="")
    ts: Mapped[datetime] = mapped_column(DateTime)
    approved_by: Mapped[str] = mapped_column(String(80), default="")


class Setting(Base):
    __tablename__ = "setting"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
