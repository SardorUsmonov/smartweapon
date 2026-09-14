"""Inventar bo'limi: /inventar (ro'yxat, tablar, filtrlar), /jihoz/{id} (karta + chain of custody),
/inventarizatsiya (sessiya: qurolxona tanlash, RFID skan simulyatsiyasi, farqlar, akt PDF)."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, Event, Officer, Region, Unit
from ..services import inventar_svc as svc
from ..services.kpi import armory_ids_for_scope
from ..services.list_scope import filter_id, location_context

router = APIRouter()

CRUMB = ("Inventar", "/inventar")


def _by(ctx: Ctx) -> str:
    return ctx.user.full_name if ctx and ctx.user else "Mehmon"


def _scope_ids(db: Session, ctx: Ctx) -> list[int] | None:
    return armory_ids_for_scope(db, ctx.scope_kind, ctx.scope_id)


def _need(ctx: Ctx, action: str = "inventar") -> None:
    if not ctx.can(action):
        raise HTTPException(status_code=403, detail="Ruxsat yo'q: faqat qurolxona mas'uli")


def _parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _armories(db: Session, ids: list[int] | None) -> list[Armory]:
    q = select(Armory).join(Unit, Unit.id == Armory.unit_id).join(Region, Region.id == Unit.region_id).order_by(Region.order, Unit.name, Armory.name)
    if ids is not None:
        q = q.where(Armory.id.in_(ids))
    return db.execute(q).scalars().all()


# ---------------- Ro'yxat ----------------
def _list_params(tur: str | None, holat: str, korik: str, hudud: str, q: str, kechikish: str, farq: str, hold: str, page: int) -> dict:
    if tur is None:
        tur = "" if (q or hold) else "qurol"
    if tur not in svc.KINDS:
        tur = ""
    region_id = int(hudud) if hudud.isdigit() else None
    return {"tur": tur, "holat": holat if holat in svc.STATE_LABEL else "", "korik": korik if korik in svc.INSP_LABEL else "",
            "hudud": region_id, "q": q.strip()[:60], "kechikish": kechikish == "1", "farq": farq == "1", "hold": hold == "1",
            "page": max(page, 1)}


def _qs_factory(params: dict):
    def qs(**kw):
        p = {**params, **kw}
        out = {}
        for k, v in p.items():
            if v in ("", None, False) and k != "tur":
                continue
            if k == "page" and v == 1:
                continue
            out[k] = "1" if v is True else v
        return urlencode(out)
    return qs


@router.get("/inventar")
def list_page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), tur: str | None = None, holat: str = "",
              korik: str = "", hudud: str = "", q: str = "", kechikish: str = "", farq: str = "", hold: str = "", page: int = 1,
              bolinma: str = "", qurolxona: str = "", xodim: str = "", berilgan: str = ""):
    from ..main import render
    params = _list_params(tur, holat, korik, hudud, q, kechikish, farq, hold, page)
    params["berilgan"] = berilgan == "1" or holat == "yo'q"
    if params["holat"] == "yo'q":
        params["holat"] = ""  # Compatibility with existing saved URLs; custody is explicit in the form.
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    ids = location["ids"]
    officer_id = filter_id(xodim)
    params.update(location["selected"], xodim=officer_id)
    if tur is None and officer_id:
        params["tur"] = ""
    f = {"kind": params["tur"], "holat": params["holat"], "korik": params["korik"], "region_id": params["hudud"], "q": params["q"],
         "kechikish": params["kechikish"], "farq": params["farq"], "hold": params["hold"], "armory_ids": ids,
         "officer_id": officer_id, "berilgan": params["berilgan"]}
    data = svc.list_items(db, f, page=params["page"])
    params["page"] = data["page"]
    counts = svc.kind_counts(db, ids, officer_id=officer_id)
    tabs = [("", "Barchasi", sum(counts.values()))] + [(k, svc.KIND_LABEL[k], counts[k]) for k in svc.KINDS]
    officer = db.get(Officer, officer_id) if officer_id else None
    if officer and location["scope_ids"] is not None and officer.armory_id not in location["scope_ids"]:
        officer = None
    location_qs = urlencode({k: v for k, v in {**location["selected"], "xodim": officer_id}.items() if v})
    return render(request, "inventar/list.html", ctx, active="inventar", breadcrumb=[CRUMB], title="Inventar",
                  p=params, qs=_qs_factory(params), tur=params["tur"], tabs=tabs, data=data, k=svc.summary(db, ids, officer_id=officer_id),
                  location_fields=location["fields"], location_qs=location_qs, selected_officer=officer,
                  STATE=svc.STATE_LABEL, INSP=svc.INSP_LABEL, KIND=svc.KIND_LABEL, per_page=svc.PER_PAGE)


@router.get("/inventar/partials/kpi")
def p_kpi(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), hudud: str = "",
          bolinma: str = "", qurolxona: str = "", xodim: str = ""):
    from ..main import render
    location = location_context(db, ctx, hudud, bolinma, qurolxona)
    officer_id = filter_id(xodim)
    location_qs = urlencode({k: v for k, v in {**location["selected"], "xodim": officer_id}.items() if v})
    return render(request, "inventar/partials/kpi.html", ctx,
                  k=svc.summary(db, location["ids"], officer_id=officer_id), location_qs=location_qs)


# ---------------- Jihoz kartasi ----------------
@router.get("/jihoz/{item_id}")
def item_page(item_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), ok: str = "", xato: str = ""):
    from ..main import render
    ids = _scope_ids(db, ctx)
    d = svc.item_detail(db, item_id, armory_ids=ids)
    if d is None:
        raise HTTPException(status_code=404, detail="Jihoz topilmadi")
    if ids is not None and (d["arm"] is None or d["arm"].id not in ids):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    item = d["item"]
    name = f"{item.model} · {item.serial}"
    return render(request, "inventar/item.html", ctx, active="inventar", breadcrumb=[CRUMB, (name, None)], title=name,
                  ok=ok, xato=xato, STATE=svc.STATE_LABEL, INSP=svc.INSP_LABEL, KIND=svc.KIND_LABEL, PANEL_STATES=svc.PANEL_STATES, **d)


def _back(item_id: int, ok: str = "", xato: str = "") -> RedirectResponse:
    tail = f"?ok={quote(ok)}" if ok else (f"?xato={quote(xato)}" if xato else "")
    return RedirectResponse(f"/jihoz/{item_id}{tail}", status_code=303)


def _load(db: Session, ctx: Ctx, item_id: int) -> dict:
    d = svc.item_detail(db, item_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Jihoz topilmadi")
    ids = _scope_ids(db, ctx)
    if ids is not None and (d["arm"] is None or d["arm"].id not in ids):
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    return d


@router.post("/jihoz/{item_id}/korik")
def item_inspection(item_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), inspection_state: str = Form(...),
                    next_inspection: str = Form(""), sabab: str = Form("")):
    _need(ctx)
    d = _load(db, ctx, item_id)
    try:
        svc.set_inspection(db, d["item"], d["cab"], d["arm"], inspection_state, _parse_date(next_inspection), sabab.strip(), _by(ctx))
    except ValueError as e:
        db.rollback()
        return _back(item_id, xato=str(e))
    db.commit()
    return _back(item_id, ok="Ko'rik holati yangilandi va jurnalga yozildi")


@router.post("/jihoz/{item_id}/holat")
def item_state(item_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), holat: str = Form(...), sabab: str = Form("")):
    _need(ctx)
    d = _load(db, ctx, item_id)
    if len(sabab.strip()) < 3:
        return _back(item_id, xato="Sabab maydoni majburiy (kamida 3 belgi)")
    try:
        svc.set_state(db, d["item"], d["cab"], d["arm"], holat, sabab.strip(), _by(ctx))
    except ValueError as e:
        db.rollback()
        return _back(item_id, xato=str(e))
    db.commit()
    return _back(item_id, ok="Jihoz holati yangilandi va jurnalga yozildi")


@router.post("/jihoz/{item_id}/hold")
def item_hold(item_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), hold: str = Form("1"), sabab: str = Form("")):
    _need(ctx)
    d = _load(db, ctx, item_id)
    if hold not in ("0", "1"):
        raise HTTPException(status_code=400, detail="Noma'lum ushlab turish holati")
    want = hold == "1"
    if want and len(sabab.strip()) < 3:
        return _back(item_id, xato="Ushlab turish uchun sabab majburiy (kamida 3 belgi)")
    if d["item"].hold == want:
        return _back(item_id, xato="Holat allaqachon shunday")
    svc.set_hold(db, d["item"], d["cab"], d["arm"], want, sabab.strip(), _by(ctx))
    db.commit()
    return _back(item_id, ok="Jihoz ushlab turildi: berish bloklandi" if want else "Ushlab turish bekor qilindi")


# ---------------- Inventarizatsiya ----------------
@router.get("/inventarizatsiya")
def inv_index(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), armory_id: int | None = None, xato: str = ""):
    from ..main import render
    ids = _scope_ids(db, ctx)
    armories = _armories(db, ids)
    sessions = [s for s in svc.sessions_all() if ids is None or s["armory_id"] in ids]
    arm_by_id = {a.id: a for a in armories}
    sel = armory_id if armory_id in arm_by_id else (ctx.scope_id if ctx.scope_kind == "qurolxona" and ctx.scope_id in arm_by_id else (armories[0].id if armories else None))
    return render(request, "inventar/inventarizatsiya.html", ctx, active="inventar", breadcrumb=[CRUMB, ("Inventarizatsiya", None)],
                  title="Inventarizatsiya", armories=armories, sel=sel, sessions=sessions, arm_by_id=arm_by_id,
                  hist=svc.history(db, ids), xato=xato)


@router.post("/inventarizatsiya/boshlash")
def inv_start(ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), armory_id: int = Form(...), masul: str = Form("")):
    _need(ctx)
    ids = _scope_ids(db, ctx)
    a = db.get(Armory, armory_id)
    if a is None or (ids is not None and a.id not in ids):
        raise HTTPException(status_code=403, detail="Qurolxona vakolat doirasidan tashqarida")
    if not a.online:
        return RedirectResponse("/inventarizatsiya?xato=" + quote("Qurolxona oflayn: inventarizatsiya faqat onlayn qurolxonada o'tkaziladi"), status_code=303)
    svc.session_start(a, masul.strip() or _by(ctx))
    return RedirectResponse(f"/inventarizatsiya/{a.id}", status_code=303)


@router.get("/inventarizatsiya/akt/{event_id}")
def inv_act(event_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    from ..main import render
    ev = db.get(Event, event_id)
    if ev is None or ev.type != "inventarizatsiya":
        raise HTTPException(status_code=404, detail="Akt topilmadi")
    ids = _scope_ids(db, ctx)
    if ids is not None and ev.armory_id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    arm = db.get(Armory, ev.armory_id) if ev.armory_id else None
    return render(request, "inventar/akt.html", ctx, active="inventar", title=f"Inventarizatsiya akti №{ev.id}",
                  breadcrumb=[CRUMB, ("Inventarizatsiya", "/inventarizatsiya"), (f"Akt №{ev.id}", None)],
                  ev=ev, arm=arm, p=ev.payload or {}, SCAN=svc.SCAN_LABEL, STATE=svc.STATE_LABEL, KIND=svc.KIND_LABEL)


@router.get("/inventarizatsiya/akt/{event_id}/pdf")
def inv_act_pdf(event_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    ev = db.get(Event, event_id)
    if ev is None or ev.type != "inventarizatsiya":
        raise HTTPException(status_code=404, detail="Akt topilmadi")
    ids = _scope_ids(db, ctx)
    if ids is not None and ev.armory_id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    arm = db.get(Armory, ev.armory_id) if ev.armory_id else None
    pdf = svc.act_pdf(ev, arm)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="inventarizatsiya-akt-{ev.id}.pdf"'})


def _session_page_ctx(db: Session, ctx: Ctx, armory_id: int):
    a = db.get(Armory, armory_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Qurolxona topilmadi")
    ids = _scope_ids(db, ctx)
    if ids is not None and a.id not in ids:
        raise HTTPException(status_code=403, detail="Vakolat doirasidan tashqarida")
    return a, svc.session_get(armory_id)


@router.get("/inventarizatsiya/{armory_id}")
def inv_session(armory_id: int, request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), xato: str = ""):
    from ..main import render
    a, s = _session_page_ctx(db, ctx, armory_id)
    if s is None:
        return RedirectResponse(f"/inventarizatsiya?armory_id={armory_id}", status_code=303)
    rows = svc.session_items(db, armory_id)
    return render(request, "inventar/sessiya.html", ctx, active="inventar", title="Inventarizatsiya sessiyasi",
                  breadcrumb=[CRUMB, ("Inventarizatsiya", "/inventarizatsiya"), (a.unit.name, None)],
                  arm=a, s=s, rows=rows, xato=xato, SCAN=svc.SCAN_LABEL, STATE=svc.STATE_LABEL, KIND=svc.KIND_LABEL,
                  DISC=svc.DISCREPANCY_CODES, step=(3 if s["scanned"] and s["discrepancies"] is not None else 1))


@router.post("/inventarizatsiya/{armory_id}/skan")
def inv_scan(armory_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    _need(ctx)
    a, s = _session_page_ctx(db, ctx, armory_id)
    if s is None:
        return RedirectResponse(f"/inventarizatsiya?armory_id={armory_id}", status_code=303)
    svc.session_scan(db, s)
    return RedirectResponse(f"/inventarizatsiya/{armory_id}#farqlar", status_code=303)


@router.post("/inventarizatsiya/{armory_id}/yakunlash")
def inv_finish(armory_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), tasdiqlovchi: str = Form(""),
               izoh: str = Form(""), hold_farq: str = Form(""), tasdiq: str = Form("")):
    _need(ctx)
    a, s = _session_page_ctx(db, ctx, armory_id)
    if s is None:
        return RedirectResponse(f"/inventarizatsiya?armory_id={armory_id}", status_code=303)
    if not s["scanned"]:
        return RedirectResponse(f"/inventarizatsiya/{armory_id}?xato=" + quote("Avval RFID skanini o'tkazing"), status_code=303)
    if tasdiq != "1":
        return RedirectResponse(f"/inventarizatsiya/{armory_id}?xato=" + quote("Aktni yakunlash uchun tasdiq belgisi majburiy"), status_code=303)
    if len(tasdiqlovchi.strip()) < 3:
        return RedirectResponse(f"/inventarizatsiya/{armory_id}?xato=" + quote("Tasdiqlovchi (ikkinchi shaxs) F.I.Sh. majburiy"), status_code=303)
    ev = svc.session_finish(db, s, a, _by(ctx), tasdiqlovchi.strip()[:80], izoh.strip()[:300], hold_farq == "1")
    db.commit()
    return RedirectResponse(f"/inventarizatsiya/akt/{ev.id}", status_code=303)


@router.post("/inventarizatsiya/{armory_id}/bekor")
def inv_cancel(armory_id: int, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    _need(ctx)
    _session_page_ctx(db, ctx, armory_id)
    svc.session_cancel(armory_id)
    return RedirectResponse("/inventarizatsiya", status_code=303)
