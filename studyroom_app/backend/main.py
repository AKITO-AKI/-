\
from __future__ import annotations

import os
import sqlite3
import secrets
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Literal, Dict, Any, List, Tuple

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from itsdangerous import URLSafeSerializer, BadSignature
from passlib.context import CryptContext

# =========================================================
# Config
# =========================================================
JST = timezone(timedelta(hours=9))

def now_jst() -> datetime:
    return datetime.now(tz=JST)

SECRET_KEY = os.getenv("STUDYROOM_SECRET_KEY") or secrets.token_urlsafe(32)
ADMIN_PASSWORD = os.getenv("STUDYROOM_ADMIN_PASSWORD") or "change-me"
DB_PATH = os.getenv("STUDYROOM_DB_PATH") or os.path.join(os.path.dirname(__file__), "studyroom.sqlite3")

serializer = URLSafeSerializer(SECRET_KEY, salt="studyroom-session")
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =========================================================
# DB helpers
# =========================================================
def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        nickname TEXT NOT NULL,
        pin_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        checkin_at TEXT NOT NULL,
        checkout_at TEXT,
        duration_sec INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

def iso(dt: datetime) -> str:
    return dt.astimezone(JST).isoformat()

def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)

def clamp_overlap_sec(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> int:
    """Return overlap seconds between [a0,a1) and [b0,b1)."""
    start = max(a0, b0)
    end = min(a1, b1)
    if end <= start:
        return 0
    return int((end - start).total_seconds())

# =========================================================
# Auth (cookie-based)
# =========================================================
def set_session_cookie(response: Response, payload: Dict[str, Any]) -> None:
    token = serializer.dumps(payload)
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True if you terminate HTTPS
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )

def clear_session_cookie(response: Response) -> None:
    response.delete_cookie("session", path="/")

def read_session(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        return serializer.loads(token)
    except BadSignature:
        return None

def require_user(request: Request) -> Dict[str, Any]:
    sess = read_session(request)
    if not sess or sess.get("type") != "user" or "user_id" not in sess:
        raise HTTPException(status_code=401, detail="Not logged in")
    return sess

def require_admin(request: Request) -> Dict[str, Any]:
    sess = read_session(request)
    if not sess or sess.get("type") != "admin":
        raise HTTPException(status_code=401, detail="Admin only")
    return sess

# =========================================================
# Models
# =========================================================
class CheckReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=4, max_length=32)

class LoginReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=4, max_length=32)

class AdminLoginReq(BaseModel):
    password: str = Field(min_length=1, max_length=128)

class CreateUserReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=64)
    nickname: str = Field(min_length=1, max_length=32)
    pin: str = Field(min_length=4, max_length=32)

class ResetPinReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)
    new_pin: str = Field(min_length=4, max_length=32)

class ForceCheckoutReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)

RangeName = Literal["today", "week", "month", "all"]

# =========================================================
# App
# =========================================================
app = FastAPI(title="StudyRoom App", version="0.2.0")

BASE_DIR = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/pages", StaticFiles(directory=os.path.join(BASE_DIR, "pages")), name="pages")

@app.on_event("startup")
def _startup():
    init_db()

# =========================================================
# Core helpers
# =========================================================
def _verify_user(student_no: str, pin: str) -> sqlite3.Row:
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE student_no = ?", (student_no,))
    row = cur.fetchone()
    conn.close()
    if not row or not pwd_ctx.verify(pin, row["pin_hash"]):
        raise HTTPException(status_code=401, detail="学籍番号またはPINが違います")
    return row

def _open_session(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM sessions
        WHERE user_id = ? AND checkout_at IS NULL
        ORDER BY checkin_at DESC
        LIMIT 1
    """, (user_id,))
    return cur.fetchone()

def _range_start_end(range_name: RangeName) -> tuple[datetime, datetime]:
    now = now_jst()
    if range_name == "all":
        # practically infinite range
        start = datetime(2000, 1, 1, tzinfo=JST)
        end = datetime(2100, 1, 1, tzinfo=JST)
        return start, end
    if range_name == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end
    if range_name == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start - timedelta(days=start.weekday())  # Monday start
        end = start + timedelta(days=7)
        return start, end
    if range_name == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end
    raise ValueError("unknown range")

def _fetch_sessions_overlapping(conn: sqlite3.Connection, start: datetime, end: datetime, user_id: Optional[int] = None):
    """
    Fetch sessions that overlap [start,end).
    IMPORTANT: This handles sessions that started before the range and ended inside/after.
    """
    cur = conn.cursor()
    if user_id is None:
        cur.execute("""
            SELECT u.id AS user_id, u.nickname AS nickname,
                   s.checkin_at AS checkin_at, s.checkout_at AS checkout_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.checkin_at < ?
              AND (s.checkout_at IS NULL OR s.checkout_at > ?)
        """, (iso(end), iso(start)))
    else:
        cur.execute("""
            SELECT u.id AS user_id, u.nickname AS nickname,
                   s.checkin_at AS checkin_at, s.checkout_at AS checkout_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.user_id = ?
              AND s.checkin_at < ?
              AND (s.checkout_at IS NULL OR s.checkout_at > ?)
        """, (user_id, iso(end), iso(start)))
    return cur.fetchall()

def _compute_totals_in_range(conn: sqlite3.Connection, start: datetime, end: datetime) -> Dict[int, Dict[str, Any]]:
    """
    Returns dict[user_id] = {"nickname": str, "total_sec": int}
    """
    rows = _fetch_sessions_overlapping(conn, start, end, user_id=None)
    now = now_jst()
    totals: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        uid = int(r["user_id"])
        nick = r["nickname"]
        ci = parse_iso(r["checkin_at"])
        co = parse_iso(r["checkout_at"]) if r["checkout_at"] else now
        sec = clamp_overlap_sec(ci, co, start, end)
        if uid not in totals:
            totals[uid] = {"nickname": nick, "total_sec": 0}
        totals[uid]["total_sec"] += sec
    return totals

def _rank_of_user(totals: Dict[int, Dict[str, Any]], user_id: int) -> Dict[str, Any]:
    """
    Competition rank: rank = 1 + count(users with strictly greater total_sec)
    """
    total_users = max(1, len(totals))
    my_sec = int(totals.get(user_id, {}).get("total_sec", 0))
    greater = sum(1 for v in totals.values() if int(v["total_sec"]) > my_sec)
    rank = greater + 1
    return {"rank": rank, "total_users": total_users, "my_sec": my_sec}

def _all_time_total_sec(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("""
        SELECT SUM(duration_sec) AS sec
        FROM sessions
        WHERE user_id = ? AND checkout_at IS NOT NULL
    """, (user_id,))
    sec = int(cur.fetchone()["sec"] or 0)
    # plus active
    cur.execute("""
        SELECT checkin_at FROM sessions
        WHERE user_id = ? AND checkout_at IS NULL
        ORDER BY checkin_at DESC LIMIT 1
    """, (user_id,))
    a = cur.fetchone()
    if a:
        ci = parse_iso(a["checkin_at"])
        sec += int((now_jst() - ci).total_seconds())
    return max(0, sec)

def _daily_series_for_all_users(conn: sqlite3.Connection, start: datetime, end: datetime) -> Tuple[List[str], Dict[int, List[int]], Dict[int, str]]:
    """
    Build daily totals per user for each day in [start,end) (day bins).
    Returns (labels, user_to_secs, user_to_nickname)
    """
    # day bins
    labels: List[str] = []
    day_starts: List[datetime] = []
    d = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while d < end:
        labels.append(d.date().isoformat())
        day_starts.append(d)
        d = d + timedelta(days=1)

    rows = _fetch_sessions_overlapping(conn, start, end, user_id=None)
    now = now_jst()

    user_to_secs: Dict[int, List[int]] = {}
    user_to_nick: Dict[int, str] = {}

    for r in rows:
        uid = int(r["user_id"])
        nick = r["nickname"]
        user_to_nick[uid] = nick
        if uid not in user_to_secs:
            user_to_secs[uid] = [0 for _ in labels]

        ci = parse_iso(r["checkin_at"])
        co = parse_iso(r["checkout_at"]) if r["checkout_at"] else now

        # distribute overlap into each day bin
        for i, ds in enumerate(day_starts):
            de = ds + timedelta(days=1)
            if de <= ci or ds >= co:
                continue
            sec = clamp_overlap_sec(ci, co, ds, de)
            if sec:
                user_to_secs[uid][i] += sec

    return labels, user_to_secs, user_to_nick

def _rank_series_for_user(labels: List[str], user_to_secs: Dict[int, List[int]], user_id: int) -> List[Dict[str, Any]]:
    """
    For each day index, compute user's rank based on that day's totals.
    """
    n_days = len(labels)
    # ensure user exists
    if user_id not in user_to_secs:
        user_to_secs[user_id] = [0 for _ in range(n_days)]

    series = []
    for i in range(n_days):
        # totals for day i
        day_totals = {uid: secs[i] for uid, secs in user_to_secs.items()}
        my_sec = int(day_totals.get(user_id, 0))
        greater = sum(1 for v in day_totals.values() if int(v) > my_sec)
        rank = greater + 1
        series.append({
            "date": labels[i],
            "sec": my_sec,
            "rank": rank,
            "total_users": max(1, len(day_totals))
        })
    return series

# =========================================================
# Routes: Pages
# =========================================================
def _html_file(filename: str) -> HTMLResponse:
    path = os.path.join(BASE_DIR, "pages", filename)
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/", response_class=HTMLResponse)
def home():
    # Home is now: check-in/out + leaderboard (single terminal friendly)
    return _html_file("home.html")

@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_page():
    return _html_file("leaderboard.html")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return _html_file("login.html")

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return _html_file("dashboard.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return _html_file("admin.html")

# legacy route kept (redirect-like)
@app.get("/kiosk", response_class=HTMLResponse)
def kiosk_legacy():
    return _html_file("home.html")

# =========================================================
# Routes: Auth
# =========================================================
@app.post("/api/login")
def login(req: LoginReq, response: Response):
    user = _verify_user(req.student_no, req.pin)
    set_session_cookie(response, {"type": "user", "user_id": int(user["id"])})
    return {"ok": True}

@app.post("/api/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}

@app.post("/api/admin/login")
def admin_login(req: AdminLoginReq, response: Response):
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="管理パスワードが違います")
    set_session_cookie(response, {"type": "admin"})
    return {"ok": True}

# =========================================================
# Routes: Check-in/out
# =========================================================
@app.post("/api/checkin")
def checkin(req: CheckReq):
    user = _verify_user(req.student_no, req.pin)
    conn = db_connect()
    cur = conn.cursor()

    open_sess = _open_session(conn, int(user["id"]))
    if open_sess:
        conn.close()
        raise HTTPException(status_code=409, detail="すでに入室中です（退室してから再入室してください）")

    t = now_jst()
    cur.execute("""
        INSERT INTO sessions (user_id, checkin_at, checkout_at, duration_sec)
        VALUES (?, ?, NULL, NULL)
    """, (int(user["id"]), iso(t)))
    conn.commit()
    conn.close()
    return {"ok": True, "message": f"{user['nickname']} 入室: {t.strftime('%H:%M:%S')}"}

@app.post("/api/checkout")
def checkout(req: CheckReq):
    user = _verify_user(req.student_no, req.pin)
    conn = db_connect()
    cur = conn.cursor()

    open_sess = _open_session(conn, int(user["id"]))
    if not open_sess:
        conn.close()
        raise HTTPException(status_code=409, detail="入室記録が見つかりません（先に入室してください）")

    t = now_jst()
    checkin_at = parse_iso(open_sess["checkin_at"])
    dur = max(0, int((t - checkin_at).total_seconds()))

    cur.execute("""
        UPDATE sessions
        SET checkout_at = ?, duration_sec = ?
        WHERE id = ?
    """, (iso(t), int(dur), int(open_sess["id"])))
    conn.commit()
    conn.close()
    return {"ok": True, "message": f"{user['nickname']} 退室: {t.strftime('%H:%M:%S')} / {dur//60}分"}

# =========================================================
# Routes: Leaderboard
# =========================================================
@app.get("/api/leaderboard")
def leaderboard(range: RangeName = "today", top: int = 20):
    if top < 1: top = 1
    if top > 100: top = 100

    start, end = _range_start_end(range)
    conn = db_connect()
    totals = _compute_totals_in_range(conn, start, end)

    items = [{"nickname": v["nickname"], "total_sec": int(v["total_sec"])} for v in totals.values()]
    items.sort(key=lambda x: x["total_sec"], reverse=True)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM sessions WHERE checkout_at IS NULL")
    occupancy = int(cur.fetchone()["c"])
    conn.close()

    return {
        "ok": True,
        "range": range,
        "start": iso(start),
        "end": iso(end),
        "occupancy": occupancy,
        "items": items[:top],
        "total_users": max(1, len(totals)),
    }

# =========================================================
# Routes: Me / Dashboard data
# =========================================================
@app.get("/api/me")
def me(request: Request, sess: Dict[str, Any] = Depends(require_user)):
    user_id = int(sess["user_id"])
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("SELECT id, student_no, name, nickname, created_at FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    # recent sessions
    cur.execute("""
        SELECT id, checkin_at, checkout_at, duration_sec
        FROM sessions
        WHERE user_id = ?
        ORDER BY checkin_at DESC
        LIMIT 30
    """, (user_id,))
    sessions = []
    for s in cur.fetchall():
        sessions.append({
            "id": int(s["id"]),
            "checkin_at": s["checkin_at"],
            "checkout_at": s["checkout_at"],
            "duration_sec": int(s["duration_sec"] or 0),
            "is_active": s["checkout_at"] is None
        })

    # totals + ranks (today/week/month/all)
    totals_out: Dict[str, int] = {}
    ranks_out: Dict[str, Any] = {}

    for rn in ["today", "week", "month"]:
        start, end = _range_start_end(rn)  # type: ignore[arg-type]
        totals = _compute_totals_in_range(conn, start, end)
        my = int(totals.get(user_id, {}).get("total_sec", 0))
        totals_out[rn] = my
        ranks_out[rn] = _rank_of_user(totals, user_id)

    totals_out["all"] = _all_time_total_sec(conn, user_id)
    # all-time rank (optional)
    start, end = _range_start_end("all")
    totals_all = _compute_totals_in_range(conn, start, end)
    ranks_out["all"] = _rank_of_user(totals_all, user_id)

    # daily trends (last 21 days)
    days = 21
    end_tr = now_jst().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start_tr = end_tr - timedelta(days=days)
    labels, user_to_secs, _ = _daily_series_for_all_users(conn, start_tr, end_tr)
    series = _rank_series_for_user(labels, user_to_secs, user_id)

    # also cumulative sum for the user (for a smooth "積み上げ推移")
    cum = 0
    cum_series = []
    for it in series:
        cum += int(it["sec"])
        cum_series.append({"date": it["date"], "cum_sec": cum})

    conn.close()

    return {
        "ok": True,
        "user": dict(user),
        "totals": totals_out,            # sec
        "ranks": ranks_out,              # per range
        "daily": series,                 # per day: sec + rank
        "daily_cum": cum_series,         # per day: cumulative seconds in window
        "sessions": sessions,
    }

# =========================================================
# Routes: Admin
# =========================================================
@app.get("/api/admin/users")
def admin_users(request: Request, _: Dict[str, Any] = Depends(require_admin)):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id, student_no, name, nickname, created_at FROM users ORDER BY created_at DESC LIMIT 500")
    users = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"ok": True, "users": users}

@app.post("/api/admin/create_user")
def admin_create_user(req: CreateUserReq, request: Request, _: Dict[str, Any] = Depends(require_admin)):
    conn = db_connect()
    cur = conn.cursor()
    pin_hash = pwd_ctx.hash(req.pin)
    try:
        cur.execute("""
            INSERT INTO users (student_no, name, nickname, pin_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (req.student_no, req.name, req.nickname, pin_hash, iso(now_jst())))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="その学籍番号は既に登録されています")
    conn.close()
    return {"ok": True}

@app.post("/api/admin/reset_pin")
def admin_reset_pin(req: ResetPinReq, request: Request, _: Dict[str, Any] = Depends(require_admin)):
    conn = db_connect()
    cur = conn.cursor()
    pin_hash = pwd_ctx.hash(req.new_pin)
    cur.execute("UPDATE users SET pin_hash = ? WHERE student_no = ?", (pin_hash, req.student_no))
    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/api/admin/force_checkout")
def admin_force_checkout(req: ForceCheckoutReq, request: Request, _: Dict[str, Any] = Depends(require_admin)):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE student_no = ?", (req.student_no,))
    u = cur.fetchone()
    if not u:
        conn.close()
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    user_id = int(u["id"])

    cur.execute("""
        SELECT * FROM sessions
        WHERE user_id = ? AND checkout_at IS NULL
        ORDER BY checkin_at DESC LIMIT 1
    """, (user_id,))
    s = cur.fetchone()
    if not s:
        conn.close()
        raise HTTPException(status_code=409, detail="入室中のセッションがありません")

    t = now_jst()
    ci = parse_iso(s["checkin_at"])
    dur = max(0, int((t - ci).total_seconds()))
    cur.execute("UPDATE sessions SET checkout_at=?, duration_sec=? WHERE id=?", (iso(t), dur, int(s["id"])))
    conn.commit()
    conn.close()
    return {"ok": True, "duration_sec": dur}

# =========================================================
# Health
# =========================================================
@app.get("/api/health")
def health():
    return {"ok": True, "time_jst": iso(now_jst())}
