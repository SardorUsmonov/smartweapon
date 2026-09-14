"""Simulyator sahifasi va harakatlari."""
from __future__ import annotations

import asyncio
from html import escape

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..deps import Ctx, get_ctx
from ..models import Armory, Cabinet, Mode, Region, Unit
from ..services import sim as simsvc

def _require_simulator(ctx: Ctx = Depends(get_ctx)):
    from ..config import DEMO_MODE
    if not DEMO_MODE or not ctx.can("simulyator"):
        raise HTTPException(403, "Simulyator respublika demo administratori uchun.")


router = APIRouter(prefix="/simulyator", dependencies=[Depends(_require_simulator)])
_auto = {"task": None, "interval": 4.0, "running": False}


@router.get("")
def page(request: Request, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db), armory_id: int | None = None):
    from ..main import render
    armories = db.execute(select(Armory).join(Unit).join(Region).order_by(Region.order, Unit.name)).scalars().all()
    armory = db.get(Armory, armory_id) if armory_id else next((a for a in armories if "Yunusobod" in a.name), armories[0])
    cabs = sorted(armory.cabinets, key=lambda c: c.position)
    modes = db.execute(select(Mode).where(Mode.ended_at.is_(None))).scalars().all()
    return render(request, "sim.html", ctx, active="simulyator", armories=armories, armory=armory, cabs=cabs, modes=modes,
                  auto=_auto, cabinet_actions=simsvc.SIMPLE, armory_actions=simsvc.ARMORY_ACTIONS, terminal_text=simsvc.TERMINAL_TEXT,
                  breadcrumb=[("Simulyator", "/simulyator")], title="Simulyator")


@router.post("/yacheyka/{cab_id}/{action}")
def cabinet_action(cab_id: int, action: str, request: Request, db: Session = Depends(get_db)):
    cab = db.get(Cabinet, cab_id)
    if cab is None:
        return JSONResponse({"ok": False, "error": "yacheyka topilmadi"}, status_code=404)
    if action == "take":
        events = simsvc.cabinet_take(db, cab)
    elif action == "take_pm":
        events = simsvc.cabinet_take(db, cab, weapon="to'pponcha")
    elif action == "return":
        events = simsvc.cabinet_return(db, cab)
    elif action == "return_mismatch":
        events = simsvc.cabinet_return(db, cab, mismatch=True)
    elif action in simsvc.SIMPLE:
        events = [simsvc.cabinet_simple(db, cab, action)]
    else:
        return JSONResponse({"ok": False, "error": "noma'lum harakat"}, status_code=400)
    db.commit()
    if request.headers.get("HX-Request"):
        refusal = next((ev for ev in events if ev.type in ("rad_etildi", "rad_etildi_takror")), None)
        if refusal:
            return HTMLResponse(f'<span class="n-red" role="status">Rad etildi: {escape(refusal.detail or refusal.title)}</span>')
        return HTMLResponse(f'<span class="ok-flash">✓ {escape(action)}</span>')
    return RedirectResponse(f"/simulyator?armory_id={cab.armory_id}", status_code=303)


@router.post("/qurolxona/{armory_id}/{action}")
def armory_action(armory_id: int, action: str, request: Request, db: Session = Depends(get_db)):
    a = db.get(Armory, armory_id)
    if a is None or action not in simsvc.ARMORY_ACTIONS:
        return JSONResponse({"ok": False}, status_code=400)
    simsvc.armory_action(db, a, action)
    db.commit()
    if request.headers.get("HX-Request"):
        return HTMLResponse(f'<span class="ok-flash">✓ {action}</span>')
    return RedirectResponse(f"/simulyator?armory_id={armory_id}", status_code=303)


@router.post("/rejim/boshlash")
def mode_start(armory_id: int = Form(...), kind: str = Form("trevoga"), started_by: str = Form("Navbatchi"), approver2: str = Form("Komandir"),
               reason: str = Form(""), db: Session = Depends(get_db)):
    a = db.get(Armory, armory_id)
    if a:
        simsvc.mode_start(db, a, kind, started_by, approver2, reason); db.commit()
    return RedirectResponse(f"/simulyator?armory_id={armory_id}", status_code=303)


@router.post("/rejim/{mode_id}/tugatish")
def mode_stop(mode_id: int, db: Session = Depends(get_db)):
    m = db.get(Mode, mode_id)
    if m and m.ended_at is None:
        simsvc.mode_stop(db, m, "Navbatchi"); db.commit()
    return RedirectResponse(f"/simulyator?armory_id={m.armory_id if m else ''}", status_code=303)


@router.post("/rejim/{mode_id}/qadam")
def mode_step(mode_id: int, n: int = Form(3), db: Session = Depends(get_db)):
    m = db.get(Mode, mode_id)
    if m and m.ended_at is None:
        simsvc.mode_progress(db, m, n); db.commit()
    return RedirectResponse(f"/simulyator?armory_id={m.armory_id if m else ''}", status_code=303)


async def _auto_loop():
    while _auto["running"]:
        db = SessionLocal()
        try:
            simsvc.random_step(db); db.commit()
        except Exception as e:  # noqa: BLE001
            db.rollback(); print("auto-sim xato:", e)
        finally:
            db.close()
        await asyncio.sleep(_auto["interval"])


@router.post("/avto/{state}")
async def auto(state: str, interval: float = Form(4.0)):
    if state == "on" and not _auto["running"]:
        _auto["running"] = True; _auto["interval"] = max(1.0, float(interval))
        _auto["task"] = asyncio.create_task(_auto_loop())
    elif state == "off":
        _auto["running"] = False
    return RedirectResponse("/simulyator", status_code=303)
