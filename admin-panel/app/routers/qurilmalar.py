"""Qurilmalar bo'limi: 5 darajali daraxt, qurilma kartasi, texnik harakatlar, zaxira nusxalash holati."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, Backup, Cabinet, Device, Event
from ..services import kpi as kpisvc
from ..services import qurilmalar_svc as svc
from ..services import backup_svc
from ..backup_models import BackupArtifact
from ..services.events import record_event
from ..services.list_scope import location_context

router = APIRouter()

XABAR = {
    "selftest_ok": ("green", "Self-test muvaffaqiyatli yakunlandi, barcha tekshiruvlar o'tdi."),
    "selftest_xato": ("red", "Self-test xato bilan yakunlandi. Signal markaziga CRITICAL signal yuborildi."),
    "sinxron": ("green", "Vaqt sinxroni bajarildi: NTP og'ishi 0 s, so'nggi aloqa yangilandi."),
    "xizmat_on": ("yellow", "Qurilma xizmat rejimiga o'tkazildi. Bu qurilma bo'yicha signallar vaqtincha e'tiborga olinmaydi."),
    "xizmat_off": ("green", "Xizmat rejimi tugatildi, qurilmaning oldingi holati tiklandi."),
    "tiklash_ok": ("green", "Nusxa alohida test fayliga tiklandi. SQLite va audit zanjiri tekshiruvdan o‘tdi."),
    "nusxa_ok": ("green", "Mahalliy SQLite nusxasi va manifest yaratildi. Fayl va audit yaxlitligi tekshirildi."),
    "nusxa_ogoh": ("yellow", "Nusxa yaratildi, SQLite yaxlit. Audit zanjirida nomuvofiqlik bor; tafsilotlar tarixda. Eski yozuvlar o‘zgartirilmadi."),
    "tiklash_ogoh": ("yellow", "Nusxa test fayliga tiklandi, SQLite yaxlit. Manbadagi audit nomuvofiqliklari tiklangan faylda ham saqlangan."),
}
XATO = {
    "sabab": "Sabab maydoni majburiy: xizmat rejimiga o'tkazish sababini kiriting.",
    "holat": "Qurilma allaqachon shu holatda.",
}


def _scope_ids(ctx: Ctx, db: Session) -> list[int] | None:
    return kpisvc.armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _require_admin(ctx: Ctx):
    if not ctx.can("qurilmalar"):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q: faqat administrator")


def _require_central(ctx: Ctx):
    if ctx.scope_kind != "respublika":
        raise HTTPException(status_code=403, detail="Markaziy zaxira nusxalar vakolat doirangizdan tashqarida")


def _who(ctx: Ctx) -> str:
    return ctx.user.username if ctx.user else "mehmon"


def _device(db: Session, dev_id: int, ctx: Ctx) -> tuple[Device, Armory]:
    dev = db.get(Device, dev_id)
    if dev is None:
        raise HTTPException(status_code=404, detail="Qurilma topilmadi")
    arm = db.get(Armory, dev.armory_id)
    ids = _scope_ids(ctx, db)
    if ids is not None and arm.id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqari")
    return dev, arm


def _qs(**kw) -> str:
    return urlencode({k: v for k, v in kw.items() if v not in ("", None, 0)})


# ---------------- ro'yxat / daraxt ----------------
@router.get("/qurilmalar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = "", hudud: str = "",
              tur: str = "", q: str = "", korinish: str = "daraxt", page: int = 1, bolinma: str = "", qurolxona: str = ""):
    from ..main import render
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    hud = location["selected"]["hudud"]
    ids = location["ids"]
    all_devs = svc.load_devices(db, ids)
    filtered = bool(holat or tur or q.strip() or any(location["selected"].values()))
    devs = svc.filter_devices(all_devs, holat=holat, tur=tur, q=q, hudud=hud)
    tree, total = svc.build_tree(db, devs, filtered)
    pg = svc.paginate(devs, page)
    kinds = sorted({d["kind"] for d in all_devs}, key=lambda k: svc.KIND_ORDER.index(k) if k in svc.KIND_ORDER else 99)
    return render(request, "qurilmalar/list.html", ctx, active="qurilmalar", breadcrumb=[("Qurilmalar", "/qurilmalar")],
                  title="Qurilmalar", tree=tree, total=total, pg=pg, s=svc.summary(db, ids), kinds=kinds, filtered=filtered,
                  f={"holat": holat, **location["selected"], "tur": tur, "q": q, "korinish": korinish},
                  qs=_qs(holat=holat, **location["selected"], tur=tur, q=q),
                  location_fields=location["fields"], location_qs=_qs(**location["selected"]),
                  KIND_LABEL=svc.KIND_LABEL, STATUS_LABEL=svc.STATUS_LABEL, STATUSES=svc.STATUSES)


@router.get("/qurilmalar/partials/holat")
def p_holat(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), hudud: str = "",
            bolinma: str = "", qurolxona: str = ""):
    from ..main import render
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    return render(request, "qurilmalar/holat_partial.html", ctx, s=svc.summary(db, location["ids"]),
                  location_qs=_qs(**location["selected"]))


@router.get("/qurilmalar/partials/kontrollerlar/{armory_id}")
def p_kontrollerlar(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    """Qurolxona yacheyka kontrollerlari (daraxtning 5-darajasi, kechiktirib yuklanadi)."""
    from ..main import render
    arm = db.get(Armory, armory_id)
    if arm is None:
        raise HTTPException(status_code=404)
    ids = _scope_ids(ctx, db)
    if ids is not None and arm.id not in ids:
        raise HTTPException(status_code=403)
    cabs = db.execute(select(Cabinet).where(Cabinet.armory_id == armory_id).order_by(Cabinet.wall, Cabinet.position)).scalars().all()
    return render(request, "qurilmalar/kontrollerlar_partial.html", ctx, armory=arm, cabs=cabs)


# ---------------- qurilma kartasi ----------------
@router.get("/qurilma/{dev_id}")
def detail(dev_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), xabar: str = "", xato: str = ""):
    from ..main import render
    dev, arm = _device(db, dev_id, ctx)
    d = svc.dev_dict(dev, arm)
    siblings = [svc.dev_dict(x, arm) for x in db.execute(select(Device).where(Device.armory_id == arm.id).order_by(Device.id)).scalars() if x.id != dev.id]
    siblings.sort(key=lambda x: (svc.KIND_ORDER.index(x["kind"]) if x["kind"] in svc.KIND_ORDER else 99, x["id"]))
    cabs = []
    if dev.kind == "terminal":
        cabs = db.execute(select(Cabinet).where(Cabinet.armory_id == arm.id).order_by(Cabinet.wall, Cabinet.position)).scalars().all()
    m = dev.metrics or {}
    region = arm.unit.region
    return render(request, "qurilmalar/detail.html", ctx, active="qurilmalar",
                  breadcrumb=[("Qurilmalar", "/qurilmalar"), (region.short, f"/hudud/{region.id}"), (arm.name, f"/qurolxona/{arm.id}"), (dev.name, None)],
                  title=dev.name, dev=dev, d=d, armory=arm, metrics=svc.metric_rows(dev), events=svc.device_events(db, dev),
                  siblings=siblings, cabs=cabs, selftest=m.get("self_test"), xizmat=m.get("xizmat"), sinxron=m.get("vaqt_sinxron"),
                  msg=XABAR.get(xabar), err=XATO.get(xato), LEVEL_CHIP={"INFO": "chip-gray", "WARNING": "chip-yellow", "CRITICAL": "chip-red", "SECURITY": "chip-yellow"})


@router.post("/qurilma/{dev_id}/self-test")
def self_test(dev_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    _require_admin(ctx)
    dev, arm = _device(db, dev_id, ctx)
    ok, checks = svc.self_test(dev, arm)
    now = datetime.now().replace(microsecond=0)
    failed = [c["label"] for c in checks if not c["ok"]]
    dev.metrics = {**(dev.metrics or {}), "self_test": {"ts": now.isoformat(), "ok": ok, "xato": failed, "tekshiruvlar": checks}}
    if ok and dev.status == "ogohlantirish":
        dev.status = "onlayn"
    if arm.online and dev.status != "xizmatda":
        dev.last_seen = now
    where = f"{arm.unit.region.short} · {arm.unit.name} · {dev.name}"
    ev = record_event(db, "texnik_xizmat", armory=arm, result="ok" if ok else "xato", approver1=_who(ctx),
                      title=f"Self-test: {svc.KIND_LABEL.get(dev.kind, dev.kind)}" + (" — o'tdi" if ok else " — xato"),
                      detail=where + (" · " + ", ".join(failed) if failed else " · barcha tekshiruvlar o'tdi"),
                      payload={"amal": "self_test", "device_id": dev.id, "qurilma": dev.name, "tur": dev.kind, "kim": _who(ctx),
                               "natija": "ok" if ok else "xato", "xato": failed})
    if not ok:
        ev2 = record_event(db, "oz_tekshiruv_xato", armory=arm, result="xato", approver1=_who(ctx),
                           title=f"O'z-tekshiruv xatosi: {dev.name}", detail=where + " · " + ", ".join(failed),
                           payload={"device_id": dev.id, "xato": failed, "kim": _who(ctx)})
        svc.notify(ev2, arm.id)
    db.commit()
    svc.notify(ev, arm.id)
    return RedirectResponse(f"/qurilma/{dev.id}?xabar=" + ("selftest_ok" if ok else "selftest_xato"), status_code=303)


@router.post("/qurilma/{dev_id}/vaqt-sinxroni")
def time_sync(dev_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    _require_admin(ctx)
    dev, arm = _device(db, dev_id, ctx)
    now = datetime.now().replace(microsecond=0)
    old = (dev.metrics or {}).get("ntp_ogish_s", 0)
    dev.metrics = {**(dev.metrics or {}), "ntp_ogish_s": 0, "vaqt_sinxron": now.isoformat()}
    dev.last_seen = now
    ev = record_event(db, "texnik_xizmat", armory=arm, approver1=_who(ctx), title=f"Vaqt sinxroni: {dev.name}",
                      detail=f"{arm.unit.region.short} · {arm.unit.name} · NTP og'ishi {old} s → 0 s",
                      payload={"amal": "vaqt_sinxroni", "device_id": dev.id, "qurilma": dev.name, "tur": dev.kind, "kim": _who(ctx),
                               "eski_ogish_s": old, "yangi_ogish_s": 0})
    db.commit()
    svc.notify(ev, arm.id)
    return RedirectResponse(f"/qurilma/{dev.id}?xabar=sinxron", status_code=303)


@router.post("/qurilma/{dev_id}/xizmat")
def service_mode(dev_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = Form("on"), sabab: str = Form("")):
    _require_admin(ctx)
    dev, arm = _device(db, dev_id, ctx)
    if holat not in ("on", "off"):
        raise HTTPException(status_code=400, detail="Noma'lum xizmat rejimi")
    now = datetime.now().replace(microsecond=0)
    who = _who(ctx)
    where = f"{arm.unit.region.short} · {arm.unit.name} · {dev.name}"
    m = dict(dev.metrics or {})
    if holat == "on":
        if not sabab.strip():
            return RedirectResponse(f"/qurilma/{dev.id}?xato=sabab", status_code=303)
        if dev.status == "xizmatda":
            return RedirectResponse(f"/qurilma/{dev.id}?xato=holat", status_code=303)
        m["xizmat"] = {"sabab": sabab.strip(), "kim": who, "boshlandi": now.isoformat(), "oldingi_holat": dev.status}
        dev.status = "xizmatda"; dev.metrics = m
        ev = record_event(db, "texnik_xizmat", armory=arm, approver1=who, reason=sabab.strip()[:60],
                          title=f"Xizmat rejimi boshlandi: {dev.name}", detail=where + " · " + sabab.strip(),
                          payload={"amal": "xizmat_rejimi_boshlandi", "device_id": dev.id, "qurilma": dev.name, "tur": dev.kind, "kim": who, "sabab": sabab.strip()})
        xabar = "xizmat_on"
    else:
        if dev.status != "xizmatda":
            return RedirectResponse(f"/qurilma/{dev.id}?xato=holat", status_code=303)
        prev = m.pop("xizmat", {}) or {}
        old_status = prev.get("oldingi_holat")
        dev.status = (old_status if old_status in ("onlayn", "oflayn", "ogohlantirish") else "ogohlantirish") if arm.online else "oflayn"
        dev.metrics = m
        if dev.status == "onlayn":
            dev.last_seen = now
        ev = record_event(db, "texnik_xizmat", armory=arm, approver1=who, reason=sabab.strip()[:60],
                          title=f"Xizmat rejimi tugadi: {dev.name}", detail=where + (" · " + sabab.strip() if sabab.strip() else ""),
                          payload={"amal": "xizmat_rejimi_tugadi", "device_id": dev.id, "qurilma": dev.name, "tur": dev.kind, "kim": who,
                                   "boshlangan": prev.get("boshlandi", ""), "boshlagan": prev.get("kim", ""), "izoh": sabab.strip()})
        xabar = "xizmat_off"
    db.commit()
    svc.notify(ev, arm.id)
    return RedirectResponse(f"/qurilma/{dev.id}?xabar={xabar}", status_code=303)


# ---------------- zaxira nusxalash ----------------
@router.get("/qurilmalar/zaxira")
def backups(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), tur: str = "", page: int = 1, xabar: str = ""):
    return _backup_page(request, ctx, db, tur=tur, page=page, xabar=xabar)


def _backup_page(request, ctx, db, *, tur="", page=1, xabar="", error="", status_code=200):
    from ..main import render
    _require_central(ctx)
    ov = svc.backup_overview(db)
    q = select(Backup).order_by(Backup.ts.desc(), Backup.id.desc())
    if tur:
        q = q.where(Backup.kind == tur)
    rows = db.execute(q).scalars().all()
    pg = svc.paginate(rows, page)
    artifacts = {a.backup_id: a for a in db.scalars(select(BackupArtifact).where(BackupArtifact.backup_id.in_([b.id for b in pg["rows"]])))}
    available = db.execute(select(Backup, BackupArtifact).join(BackupArtifact, Backup.id == BackupArtifact.backup_id)
                           .where(Backup.kind.in_(["kunlik", "haftalik"])).order_by(Backup.ts.desc(), Backup.id.desc()).limit(100)).all()
    response = render(request, "qurilmalar/zaxira.html", ctx, active="qurilmalar", breadcrumb=[("Qurilmalar", "/qurilmalar"), ("Zaxira nusxalash", None)],
                      title="Zaxira nusxalash", ov=ov, pg=pg, tur=tur, qs=_qs(tur=tur), msg=XABAR.get(xabar), error=error,
                      KIND=svc.BACKUP_KIND_LABEL, artifacts=artifacts, available=available)
    response.status_code = status_code
    return response


def _backup_error(request, ctx, db, exc, operation):
    db.rollback()
    record_event(db, "zaxira_nusxa_xato", approver1=_who(ctx), result="xato", simulated=False, make_alarm=False,
                 title="Zaxira amali bajarilmadi", detail=str(exc), payload={"operation": operation, "kim": _who(ctx)})
    db.commit()
    return _backup_page(request, ctx, db, error=str(exc), status_code=exc.status_code)


@router.post("/qurilmalar/zaxira/tiklash-sinovi")
def restore_test(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), izoh: str = Form(""), backup_id: str = Form("")):
    _require_admin(ctx)
    _require_central(ctx)
    try:
        if backup_id and (not backup_id.isdigit() or int(backup_id) <= 0):
            raise backup_svc.BackupError("Nusxani ro‘yxatdan tanlang.")
        result = backup_svc.restore_test(db, _who(ctx), int(backup_id) if backup_id else None, izoh)
    except backup_svc.BackupError as exc:
        return _backup_error(request, ctx, db, exc, "restore_test")
    status = "tiklash_ogoh" if result.manifest["audit"]["broken"] else "tiklash_ok"
    return RedirectResponse("/qurilmalar/zaxira?xabar=" + status, status_code=303)


@router.post("/qurilmalar/zaxira/nusxa")
def manual_backup(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), tur: str = Form("kunlik"), izoh: str = Form("")):
    _require_admin(ctx)
    _require_central(ctx)
    try:
        result = backup_svc.create_backup(db, _who(ctx), tur, izoh)
    except backup_svc.BackupError as exc:
        return _backup_error(request, ctx, db, exc, "backup")
    status = "nusxa_ogoh" if result.manifest["audit"]["broken"] else "nusxa_ok"
    return RedirectResponse("/qurilmalar/zaxira?xabar=" + status, status_code=303)
