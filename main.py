import asyncio
import os
import sqlite3
import time
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
)

def red_btn(text: str, callback: str = None, url: str = None):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback,
        url=url
    )


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "orders.sqlite")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BANNER_PATH = os.path.join(BASE_DIR, os.getenv("BANNER_PATH", "banner.jpg"))

STANDARD_KEYS_FILE = os.path.join(BASE_DIR, "standard_keys.txt")
PREMIUM_KEYS_FILE = os.path.join(BASE_DIR, "premium_keys.txt")
FAMILY_KEYS_FILE = os.path.join(BASE_DIR, "family_keys.txt")

TG_CHANNEL = "https://t.me/tinkervpn"
TG_CHANNEL_USERNAME = "@tinkervpn"
PRIVATE_GROUP_LINK = "https://t.me/tinkervpn"
REVIEW_LINK = "https://t.me/otzivi8989"
AGREEMENT_URL = "https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10"

HAPP_ANDROID_URL = "https://play.google.com/store/apps/details?id=com.happproxy"
HAPP_IOS_URL = "https://apps.apple.com/app/happ-proxy-utility/id6504287215"
HAPP_WINDOWS_URL = "https://happ.su/"

RESEND_COOLDOWN_SEC = 10 * 60
RESEND_MAX = 3
USERS_PAGE_SIZE = 10

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())


class AdminStates(StatesGroup):
    broadcast_wait = State()
    search_wait = State()
    keys_wait = State()
    key_delete_wait = State()
    price_wait = State()
    message_user_wait = State()


def html_escape(v: Any) -> str:
    return (
        str(v or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def now_ts() -> int:
    return int(time.time())


def plan_visible_name(plan: str) -> str:
    names = {
        "standard": "📦 Standart",
        "premium": "⚡ Premium",
        "family": "👨‍👩‍👧‍👦 Family",
    }
    return names.get(plan, plan)


def plan_plain_name(plan: str) -> str:
    names = {
        "standard": "Standart",
        "premium": "Premium",
        "family": "Family",
    }
    return names.get(plan, plan)


def plan_conditions(plan: str) -> str:
    if plan == "standard":
        return "👤 1 пользователь • 📱 до 3 устройств"
    if plan == "premium":
        return "👤 1 пользователь • 📱 до 3 устройств\n🚀 Отдельные хост сервера с топовой скоростью"
    return "👥 до 5 пользователей • 📱 до 10 устройств"


def payment_text_html() -> str:
    return (
        "💳 <b>Оплата подписки</b>\n\n"
        "┏ <b>Реквизиты [На озон]</b>\n"
        "┣ Карта: <code>2204320644631782</code>\n"
        "┗ Номер: <code>+79224545065</code>\n\n"
        "📎 После оплаты отправь сюда <b>чек или скрин</b>.\n"
        "✅ После проверки бот мгновенно выдаст тебе ключ доступа."
    )


def text_menu() -> str:
    return (
        "🌐 <b>Tinker VPN</b>\n"
        "<i>Private access • Fast route • Clean UI</i>\n\n"
        "╭ <b>Что внутри</b>\n"
        "├ ⚡ Быстрое и стабильное подключение\n"
        "├ 🛡️ Обход блокировок и цензуры\n"
        "├ 📱 Удобное подключение через Happ\n"
        "└ ✅ Выдача ключа после подтверждения оплаты\n\n"
        "Выбери нужный раздел ниже 👇"
    )


def text_buy_intro() -> str:
    std_price = plan_meta("standard")[3]
    pr_price = plan_meta("premium")[3]
    fam_price = plan_meta("family")[3]

    return (
        "💠 <b>Тарифы Tinker VPN</b>\n\n"
        f"📦 <b>Standart</b>\n"
        f"├ 1 пользователь\n"
        f"├ До 3 устройств\n"
        f"└ <b>{std_price}₽</b>\n\n"
        f"⚡ <b>Premium</b>\n"
        f"├ 1 пользователь\n"
        f"├ До 3 устройств\n"
        f"├ Отдельные хост сервера\n"
        f"└ <b>{pr_price}₽</b>\n\n"
        f"👨‍👩‍👧‍👦 <b>Family</b>\n"
        f"├ До 5 пользователей\n"
        f"├ До 10 устройств\n"
        f"└ <b>{fam_price}₽</b>\n\n"
        "Выбери тариф ниже и отправь чек после оплаты."
    )


def format_ts(ts: Optional[int]) -> str:
    if not ts:
        return "—"
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts))


def plan_meta(plan: str):
    price_standard = int(db_settings_get("price_standard", "75") or 75)
    price_premium = int(db_settings_get("price_premium", "300") or 300)
    price_family = int(db_settings_get("price_family", "150") or 150)

    if plan == "standard":
        return "📦 Standart", "👤 1 пользователь • 📱 до 3 устройств", "3", price_standard
    if plan == "premium":
        return "⚡ Premium", "👤 1 пользователь • 📱 до 3 устройств • 🚀 отдельные хост сервера", "3", price_premium
    return "👨‍👩‍👧‍👦 Family", "👥 до 5 пользователей • 📱 до 10 устройств", "10", price_family


def db():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def db_init():
    con = db()
    try:
        cur = con.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_seen INTEGER,
            is_blocked INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            payment_msg_id INTEGER,
            issued_key TEXT,
            accepted_at INTEGER,
            admin_msg_id INTEGER,
            resend_count INTEGER DEFAULT 0,
            last_resend_at INTEGER DEFAULT 0
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            issued_key TEXT,
            is_active INTEGER DEFAULT 1,
            order_id INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(user_id, plan)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS keys_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan TEXT NOT NULL,
            key TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            used_at INTEGER,
            order_id INTEGER
        )
        """)

        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_keys_plan_key ON keys_store(plan, key)")

        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('price_standard', '75')")
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('price_premium', '300')")
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('price_family', '150')")

        cur.execute("""
        INSERT INTO subscriptions(user_id, plan, issued_key, is_active, order_id, created_at, updated_at)
        SELECT o.user_id, o.plan, o.issued_key, 1, o.id,
               COALESCE(o.accepted_at, o.created_at), COALESCE(o.accepted_at, o.created_at)
        FROM orders o
        WHERE o.status='accepted' AND COALESCE(o.issued_key, '') <> ''
          AND NOT EXISTS (
              SELECT 1 FROM subscriptions s
              WHERE s.user_id=o.user_id AND s.plan=o.plan
          )
        """)

        con.commit()
    finally:
        con.close()


def db_settings_get(key: str, default: Optional[str] = None) -> Optional[str]:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else default
    finally:
        con.close()


def db_settings_set(key: str, value: str):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        con.commit()
    finally:
        con.close()


def db_upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO users(user_id, username, first_name, last_seen, is_blocked, is_banned)
        VALUES(?,?,?,?,0,0)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_seen=excluded.last_seen
        """, (user_id, username, first_name, now_ts()))
        con.commit()
    finally:
        con.close()


def db_get_user(user_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT user_id, username, first_name, last_seen, is_blocked, is_banned FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "first_name": row[2],
            "last_seen": row[3],
            "is_blocked": row[4] or 0,
            "is_banned": row[5] or 0,
        }
    finally:
        con.close()


def db_is_banned(user_id: int) -> bool:
    user = db_get_user(user_id)
    return bool(user and user["is_banned"])


def db_create_order(user_id: int, username: Optional[str], plan: str, amount: int) -> int:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        INSERT INTO orders(user_id, username, plan, amount, status, created_at)
        VALUES(?,?,?,?,?,?)
        """, (user_id, username, plan, amount, "waiting_receipt", now_ts()))
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()


def db_get_active_order(user_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT id, user_id, username, plan, amount, status,
               payment_msg_id, issued_key, accepted_at, admin_msg_id,
               resend_count, last_resend_at, created_at
        FROM orders
        WHERE user_id=? AND status IN ('waiting_receipt', 'pending_admin')
        ORDER BY id DESC
        LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "plan": row[3],
            "amount": row[4],
            "status": row[5],
            "payment_msg_id": row[6],
            "issued_key": row[7],
            "accepted_at": row[8],
            "admin_msg_id": row[9],
            "resend_count": row[10] or 0,
            "last_resend_at": row[11] or 0,
            "created_at": row[12],
        }
    finally:
        con.close()


def db_get_order(order_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT id, user_id, username, plan, amount, status,
               payment_msg_id, issued_key, accepted_at, admin_msg_id,
               resend_count, last_resend_at, created_at
        FROM orders WHERE id=?
        """, (order_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "plan": row[3],
            "amount": row[4],
            "status": row[5],
            "payment_msg_id": row[6],
            "issued_key": row[7],
            "accepted_at": row[8],
            "admin_msg_id": row[9],
            "resend_count": row[10] or 0,
            "last_resend_at": row[11] or 0,
            "created_at": row[12],
        }
    finally:
        con.close()


def db_set_status(order_id: int, status: str):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        con.commit()
    finally:
        con.close()


def db_set_payment_msg(order_id: int, msg_id: Optional[int]):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE orders SET payment_msg_id=? WHERE id=?", (msg_id, order_id))
        con.commit()
    finally:
        con.close()


def db_set_admin_msg(order_id: int, msg_id: Optional[int]):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE orders SET admin_msg_id=? WHERE id=?", (msg_id, order_id))
        con.commit()
    finally:
        con.close()


def db_set_issued(order_id: int, key: str):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE orders SET issued_key=?, accepted_at=? WHERE id=?", (key, now_ts(), order_id))
        con.commit()
    finally:
        con.close()


def db_list_pending(limit: int = 20):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT id, user_id, username, plan, amount, created_at
        FROM orders
        WHERE status='pending_admin'
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        return cur.fetchall()
    finally:
        con.close()


def db_get_accepted_subscriptions(user_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT id, plan, issued_key, created_at, updated_at, order_id
        FROM subscriptions
        WHERE user_id=? AND is_active=1
        ORDER BY updated_at DESC, id DESC
        """, (user_id,))
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "plan": row[1],
                "amount": plan_meta(row[1])[3],
                "issued_key": row[2],
                "accepted_at": row[4] or row[3],
                "order_id": row[5],
            }
            for row in rows
        ]
    finally:
        con.close()


def db_upsert_subscription(user_id: int, plan: str, key: str, order_id: Optional[int] = None):
    con = db()
    try:
        cur = con.cursor()
        ts = now_ts()
        cur.execute("""
        INSERT INTO subscriptions(user_id, plan, issued_key, is_active, order_id, created_at, updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(user_id, plan) DO UPDATE SET
            issued_key=excluded.issued_key,
            is_active=1,
            order_id=excluded.order_id,
            updated_at=excluded.updated_at
        """, (user_id, plan, key, 1, order_id, ts, ts))
        con.commit()
    finally:
        con.close()


def db_update_user_plan_key(user_id: int, plan: str, new_key: str) -> int:
    con = db()
    try:
        cur = con.cursor()
        ts = now_ts()
        cur.execute("""
        UPDATE subscriptions
        SET issued_key=?, updated_at=?, is_active=1
        WHERE user_id=? AND plan=?
        """, (new_key, ts, user_id, plan))
        updated = cur.rowcount or 0
        cur.execute("""
        UPDATE orders
        SET issued_key=?, accepted_at=?
        WHERE user_id=? AND plan=? AND status='accepted'
        """, (new_key, ts, user_id, plan))
        con.commit()
        return updated
    finally:
        con.close()


def db_can_resend(order_id: int) -> Tuple[bool, int]:
    order = db_get_order(order_id)
    if not order:
        return False, 0

    resend_count = order["resend_count"] or 0
    last_resend_at = order["last_resend_at"] or 0

    if resend_count >= RESEND_MAX:
        remain = max(0, RESEND_COOLDOWN_SEC - (now_ts() - last_resend_at))
        return False, remain

    if last_resend_at and now_ts() - last_resend_at < RESEND_COOLDOWN_SEC:
        remain = RESEND_COOLDOWN_SEC - (now_ts() - last_resend_at)
        return False, remain

    return True, 0


def db_mark_resend(order_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        UPDATE orders
        SET resend_count=COALESCE(resend_count,0)+1,
            last_resend_at=?
        WHERE id=?
        """, (now_ts(), order_id))
        con.commit()
    finally:
        con.close()


def db_search_orders(q: str, limit: int = 20):
    q = (q or "").strip()
    username_query = q.lstrip("@")

    con = db()
    try:
        cur = con.cursor()

        if q.isdigit():
            num = int(q)

            cur.execute("""
                SELECT id, user_id, username, plan, amount, status, created_at, accepted_at
                FROM orders
                WHERE id=?
                LIMIT 1
            """, (num,))
            rows = cur.fetchall()
            if rows:
                return rows

            cur.execute("""
                SELECT id, user_id, username, plan, amount, status, created_at, accepted_at
                FROM orders
                WHERE user_id=?
                ORDER BY id DESC
                LIMIT ?
            """, (num, limit))
            rows = cur.fetchall()
            if rows:
                return rows

        cur.execute("""
            SELECT id, user_id, username, plan, amount, status, created_at, accepted_at
            FROM orders
            WHERE LOWER(COALESCE(username, '')) = LOWER(?)
            ORDER BY id DESC
            LIMIT ?
        """, (username_query, limit))
        rows = cur.fetchall()
        if rows:
            return rows

        cur.execute("""
            SELECT id, user_id, username, plan, amount, status, created_at, accepted_at
            FROM orders
            WHERE LOWER(COALESCE(username, '')) LIKE LOWER(?)
            ORDER BY id DESC
            LIMIT ?
        """, (f"%{username_query}%", limit))
        rows = cur.fetchall()
        if rows:
            return rows

        cur.execute("""
            SELECT id, user_id, username, plan, amount, status, created_at, accepted_at
            FROM orders
            WHERE LOWER(plan) LIKE LOWER(?) OR LOWER(status) LIKE LOWER(?)
            ORDER BY id DESC
            LIMIT ?
        """, (f"%{q}%", f"%{q}%", limit))
        return cur.fetchall()
    finally:
        con.close()


def db_users_stats():
    con = db()
    try:
        cur = con.cursor()
        now_ = now_ts()
        day_ago = now_ - 86400
        week_ago = now_ - 86400 * 7

        cur.execute("SELECT COUNT(*) FROM users")
        total = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM users WHERE is_blocked=1")
        blocked = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        banned = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen>=?", (day_ago,))
        active_24h = int(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen>=?", (week_ago,))
        active_7d = int(cur.fetchone()[0] or 0)

        return {
            "total": total,
            "blocked": blocked,
            "banned": banned,
            "active_24h": active_24h,
            "active_7d": active_7d,
        }
    finally:
        con.close()


def db_list_users(offset: int = 0, limit: int = USERS_PAGE_SIZE):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT user_id, username, first_name, last_seen, is_blocked, is_banned
        FROM users
        ORDER BY last_seen DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
        return cur.fetchall()
    finally:
        con.close()


def db_list_banned_users(offset: int = 0, limit: int = USERS_PAGE_SIZE):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT user_id, username, first_name, last_seen, is_blocked, is_banned
        FROM users
        WHERE is_banned=1
        ORDER BY last_seen DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
        return cur.fetchall()
    finally:
        con.close()


def db_count_users() -> int:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return int(cur.fetchone()[0] or 0)
    finally:
        con.close()


def db_count_banned_users() -> int:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE is_banned=1")
        return int(cur.fetchone()[0] or 0)
    finally:
        con.close()


def db_set_banned(user_id: int, flag: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE users SET is_banned=? WHERE user_id=?", (flag, user_id))
        con.commit()
    finally:
        con.close()


def db_ban_user_and_revoke(user_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))

        cur.execute("""
        UPDATE orders
        SET status='revoked', issued_key=NULL
        WHERE user_id=? AND status='accepted'
        """, (user_id,))

        cur.execute("""
        UPDATE orders
        SET status='cancelled'
        WHERE user_id=? AND status IN ('waiting_receipt','pending_admin')
        """, (user_id,))

        cur.execute(
            "UPDATE subscriptions SET is_active=0, updated_at=? WHERE user_id=?",
            (now_ts(), user_id)
        )

        con.commit()
    finally:
        con.close()


def db_unban_user(user_id: int):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("UPDATE users SET is_banned=0, last_seen=? WHERE user_id=?", (now_ts(), user_id))
        con.commit()
    finally:
        con.close()


def db_get_recent_orders_by_user(user_id: int, limit: int = 10):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
        SELECT id, plan, amount, status, created_at, accepted_at, issued_key
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
        """, (user_id, limit))
        return cur.fetchall()
    finally:
        con.close()


def admin_issue_subscription(user_id: int, plan: str) -> Tuple[bool, str]:
    user = db_get_user(user_id)
    username = user["username"] if user else None
    _, _, _, price = plan_meta(plan)

    key = take_key(plan, 0)
    if not key:
        return False, "Нет ключей для этого тарифа"

    order_id = db_create_order(user_id, username, plan, price)
    db_set_status(order_id, "accepted")
    db_set_issued(order_id, key)
    db_upsert_subscription(user_id, plan, key, order_id)
    return True, key


def text_admin_user_card(user_id: int) -> str:
    user = db_get_user(user_id)
    if not user:
        return "Пользователь не найден."

    uname = f"@{user['username']}" if user["username"] else "—"
    subs = db_get_accepted_subscriptions(user_id)
    recent = db_get_recent_orders_by_user(user_id, 8)

    lines = [
        "👤 <b>Карточка пользователя</b>",
        "",
        f"🆔 ID: <code>{user['user_id']}</code>",
        f"👤 Username: {html_escape(uname)}",
        f"📝 Имя: {html_escape(user['first_name'] or '—')}",
        f"🕒 Последняя активность: <b>{format_ts(user['last_seen'])}</b>",
        f"⛔ Бан: <b>{'Да' if user['is_banned'] else 'Нет'}</b>",
        "",
        "🔑 <b>Активные подписки</b>",
    ]

    if not subs:
        lines.append("• Нет активных подписок")
    else:
        for sub in subs:
            lines.append(
                f"• {plan_visible_name(sub['plan'])} — <code>{html_escape(sub['issued_key'] or '—')}</code>"
            )

    lines.extend(["", "🧾 <b>Последние заказы</b>"])

    if not recent:
        lines.append("• Заказов нет")
    else:
        for oid, plan, amount, status, created_at, accepted_at, issued_key in recent:
            lines.append(
                f"• <code>#{oid}</code> {plan_visible_name(plan)} • {amount}₽ • {html_escape(status)}"
            )

    return "\n".join(lines)


def db_keys_count(plan: str) -> int:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM keys_store WHERE plan=?", (plan,))
        return int(cur.fetchone()[0] or 0)
    finally:
        con.close()


def db_keys_add(plan: str, keys: List[str]) -> Tuple[int, int]:
    con = db()
    try:
        cur = con.cursor()
        added, skipped = 0, 0
        for k in keys:
            k = k.strip()
            if not k:
                continue
            cur.execute(
                "INSERT OR IGNORE INTO keys_store(plan, key, used, used_at, order_id) VALUES(?,?,0,NULL,NULL)",
                (plan, k)
            )
            if cur.rowcount == 1:
                added += 1
            else:
                skipped += 1
        con.commit()
        return added, skipped
    finally:
        con.close()


def db_keys_clear(plan: str):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM keys_store WHERE plan=?", (plan,))
        con.commit()
    finally:
        con.close()


def db_keys_delete_exact(plan: str, key: str) -> int:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("DELETE FROM keys_store WHERE plan=? AND key=?", (plan, key.strip()))
        con.commit()
        return cur.rowcount or 0
    finally:
        con.close()


def db_keys_get_sample(plan: str, limit: int = 5):
    con = db()
    try:
        cur = con.cursor()
        cur.execute("SELECT id, key FROM keys_store WHERE plan=? ORDER BY id DESC LIMIT ?", (plan, limit))
        return cur.fetchall()
    finally:
        con.close()


def take_key(plan: str, order_id: int = 0) -> Optional[str]:
    """
    Логика выдачи ключа:
    1) Сначала берём первый неиспользованный ключ для тарифа.
    2) Если новых ключей нет, повторно используем последний существующий ключ этого тарифа.

    Это нужно, чтобы один и тот же рабочий ключ тарифа можно было выдать нескольким
    пользователям, если в базе хранится только одна ссылка / один ключ на тариф.
    """
    con = db()
    try:
        cur = con.cursor()
        cur.execute("BEGIN IMMEDIATE")

        # Пытаемся выдать новый, ещё не использованный ключ
        cur.execute(
            "SELECT id, key FROM keys_store WHERE plan=? AND used=0 ORDER BY id ASC LIMIT 1",
            (plan,)
        )
        row = cur.fetchone()

        if row:
            key_id, key = row
            cur.execute(
                "UPDATE keys_store SET used=1, used_at=?, order_id=? WHERE id=?",
                (now_ts(), order_id or None, key_id)
            )
            con.commit()
            return key

        # Если новых ключей нет — повторно используем последний ключ тарифа
        cur.execute(
            "SELECT key FROM keys_store WHERE plan=? ORDER BY id DESC LIMIT 1",
            (plan,)
        )
        row = cur.fetchone()
        if row:
            con.commit()
            return row[0]

        con.rollback()
        return None
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def get_latest_key_for_plan(plan: str) -> Optional[str]:
    con = db()
    try:
        cur = con.cursor()
        cur.execute("""
            SELECT key
            FROM keys_store
            WHERE plan=? AND used=0
            ORDER BY id DESC
            LIMIT 1
        """, (plan,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        con.close()


def import_keys_from_files_if_empty():
    std = db_keys_count("standard")
    prm = db_keys_count("premium")
    fam = db_keys_count("family")

    if std == 0 and os.path.exists(STANDARD_KEYS_FILE):
        with open(STANDARD_KEYS_FILE, "r", encoding="utf-8") as f:
            keys = [x.strip() for x in f.read().splitlines() if x.strip()]
        if keys:
            db_keys_add("standard", keys)

    if prm == 0 and os.path.exists(PREMIUM_KEYS_FILE):
        with open(PREMIUM_KEYS_FILE, "r", encoding="utf-8") as f:
            keys = [x.strip() for x in f.read().splitlines() if x.strip()]
        if keys:
            db_keys_add("premium", keys)

    if fam == 0 and os.path.exists(FAMILY_KEYS_FILE):
        with open(FAMILY_KEYS_FILE, "r", encoding="utf-8") as f:
            keys = [x.strip() for x in f.read().splitlines() if x.strip()]
        if keys:
            db_keys_add("family", keys)


def reply_main():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Купить"), KeyboardButton(text="🔑 Мои подписки")],
            [KeyboardButton(text="📢 Канал"), KeyboardButton(text="🆘 Поддержка")],
        ],
        resize_keyboard=True
    )


def kb_menu_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            red_btn("🛒 Купить доступ", "menu:buy"),
            red_btn("🔑 Мои ключи", "menu:subs")
        ],
        [
            InlineKeyboardButton(text="📢 Наш канал", url=TG_CHANNEL),
            InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/zzztruee")
        ],
        [
            InlineKeyboardButton(text="📄 Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-08-15-10")
        ],
        [
            InlineKeyboardButton(text="🔐 Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-08-15-17")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/otzivi8989")
        ]
    ])


def kb_buy():
    return InlineKeyboardMarkup(inline_keyboard=[
        [red_btn("📦 Standart • 75₽", "buy:standard")],
        [red_btn("⚡ Premium • 300₽", "buy:premium")],
        [red_btn("👨‍👩‍👧‍👦 Family • 150₽", "buy:family")],
        [InlineKeyboardButton(text="🏠 Назад", callback_data="menu:main")]
    ])


def kb_pending_admin(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{order_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{order_id}")],
        [InlineKeyboardButton(text="👀 Открыть заказ", callback_data=f"admin:view:{order_id}")],
    ])


def kb_sub_with_refresh(user_id: int):
    rows = []
    subs = db_get_accepted_subscriptions(user_id)

    for sub in subs:
        plan = sub["plan"]
        rows.append([
            InlineKeyboardButton(
                text=plan_visible_name(plan),
                callback_data=f"sub:key:{plan}"
            )
        ])

    rows.append([InlineKeyboardButton(text="🔄 Обновить ключ", callback_data="sub:refresh")])

    active = db_get_active_order(user_id)
    if active:
        rows.append([InlineKeyboardButton(text="❌ Отменить заказ", callback_data="menu:cancel_order")])

    rows.extend([
        [InlineKeyboardButton(text="📱 Android", url=HAPP_ANDROID_URL),
         InlineKeyboardButton(text="🍎 iPhone", url=HAPP_IOS_URL)],
        [InlineKeyboardButton(text="💻 Windows", url=HAPP_WINDOWS_URL)],
        [InlineKeyboardButton(text="📢 Канал", url=TG_CHANNEL)],
        [InlineKeyboardButton(text="⭐ Оставить отзыв", url=REVIEW_LINK)],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            red_btn("📦 Заказы", "admin:list"),
            red_btn("🔎 Поиск", "admin:search")
        ],
        [
            red_btn("👥 Пользователи", "admin:users:0"),
            red_btn("⛔ Баны", "admin:banned:0")
        ],
        [
            red_btn("🔑 Ключи", "admin:keys"),
            red_btn("🏷 Цены", "admin:prices")
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")
        ]
    ])


def kb_admin_list(rows):
    keyboard = []
    for oid, uid, uname, plan, amount, created_at in rows[:20]:
        u = f"@{uname}" if uname else str(uid)
        badge = "📦" if plan == "standard" else "⚡" if plan == "premium" else "👨‍👩‍👧‍👦"
        keyboard.append([InlineKeyboardButton(
            text=f"{badge} #{oid} • {amount}₽ • {u}",
            callback_data=f"admin:view:{oid}"
        )])

    keyboard.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:list"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def kb_admin_order(order_id: int, user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{order_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{order_id}")],
        [InlineKeyboardButton(text="✉️ Написать", callback_data=f"msguser:{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:list")],
    ])


def kb_admin_users_page(offset: int, total: int, users_rows, banned: bool = False):
    prev_offset = max(0, offset - USERS_PAGE_SIZE)
    next_offset = offset + USERS_PAGE_SIZE
    prefix = "admin:banned" if banned else "admin:users"

    rows = []
    for uid, username, first_name, last_seen, is_blocked, is_banned in users_rows:
        uname = f"@{username}" if username else str(uid)
        mark = "⛔ " if is_banned else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{first_name or '—'} • {uname}",
                callback_data=f"admin:usercard:{uid}"
            )
        ])

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}:{prev_offset}"))
    if next_offset < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}:{next_offset}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_user_actions(user_id: int, is_banned_flag: bool):
    rows = []
    if is_banned_flag:
        rows.append([InlineKeyboardButton(text="✅ Разбанить", callback_data=f"admin:unban:{user_id}")])
    else:
        rows.append([InlineKeyboardButton(text="⛔ Забанить", callback_data=f"admin:ban:{user_id}")])

    rows.append([InlineKeyboardButton(text="✉️ Написать", callback_data=f"msguser:{user_id}")])
    rows.append([
        InlineKeyboardButton(text="📦 Выдать Standart", callback_data=f"admin:issue:{user_id}:standard")
    ])
    rows.append([
        InlineKeyboardButton(text="⚡ Выдать Premium", callback_data=f"admin:issue:{user_id}:premium")
    ])
    rows.append([
        InlineKeyboardButton(text="👨‍👩‍👧‍👦 Выдать Family", callback_data=f"admin:issue:{user_id}:family")
    ])
    rows.append([InlineKeyboardButton(text="🔄 Обновить карточку", callback_data=f"admin:usercard:{user_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_keys():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            red_btn("➕ Standart", "admin:keyadd:standard"),
            red_btn("🗑 Удалить", "admin:keydelete:standard")
        ],
        [
            red_btn("➕ Premium", "admin:keyadd:premium"),
            red_btn("🗑 Удалить", "admin:keydelete:premium")
        ],
        [
            red_btn("➕ Family", "admin:keyadd:family"),
            red_btn("🗑 Удалить", "admin:keydelete:family")
        ],
        [
            red_btn("🧹 Очистить Standart", "admin:keyclear:standard")
        ],
        [
            red_btn("🧹 Очистить Premium", "admin:keyclear:premium")
        ],
        [
            red_btn("🧹 Очистить Family", "admin:keyclear:family")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")
        ]
    ])


def kb_admin_prices():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Standart", callback_data="admin:price:standard")],
        [InlineKeyboardButton(text="✏️ Premium", callback_data="admin:price:premium")],
        [InlineKeyboardButton(text="✏️ Family", callback_data="admin:price:family")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")],
    ])


def text_subscription_card(from_user, subs: Optional[list]):
    name = html_escape((from_user.first_name or "—").strip())
    uid = from_user.id

    lines = [
        "🛡 <b>Личный кабинет Tinker VPN</b>",
        "",
        f"👤 <b>Профиль:</b> {name}",
        f"🆔 <b>ID:</b> <code>{uid}</code>",
        ""
    ]

    if not subs:
        lines.append("У тебя пока нет активных подписок. Оформи тариф в разделе <b>Купить</b>.")
        return "\n".join(lines)

    for sub in subs:
        lines.extend([
            f"{plan_visible_name(sub['plan'])}",
            f"├ Статус: <b>Активна</b>",
            f"├ Цена: <b>{sub['amount']}₽</b>",
            f"├ Выдано: <b>{format_ts(sub['accepted_at'])}</b>",
            f"└ Ключ: <code>{html_escape(sub['issued_key'] or '—')}</code>",
            ""
        ])

    return "\n".join(lines)


def text_order_created(order_id: int, plan: str, amount: int) -> str:
    return (
        f"🧾 <b>Заказ оформлен</b>\n\n"
        f"├ Номер: <code>#{order_id}</code>\n"
        f"├ Тариф: <b>{plan_visible_name(plan)}</b>\n"
        f"├ Цена: <b>{amount}₽</b>\n"
        f"└ {plan_conditions(plan)}\n\n"
        f"{payment_text_html()}"
    )


def text_order_to_admin(order: Dict[str, Any]) -> str:
    uname = f"@{order['username']}" if order["username"] else "—"
    return (
        "💸 <b>Новая заявка на оплату</b>\n\n"
        f"🧾 Заказ: <code>#{order['id']}</code>\n"
        f"👤 User ID: <code>{order['user_id']}</code>\n"
        f"👤 Username: {html_escape(uname)}\n"
        f"📦 Тариф: <b>{plan_visible_name(order['plan'])}</b>\n"
        f"💰 Сумма: <b>{order['amount']}₽</b>\n"
        f"🕒 Создан: <b>{format_ts(order['created_at'])}</b>\n\n"
        "Ниже прикреплён чек / скрин."
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    db_upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    if db_is_banned(message.from_user.id):
        return await message.answer("⛔ Твой доступ к боту ограничен.")

    if os.path.exists(BANNER_PATH):
        try:
            await message.answer_photo(
                photo=FSInputFile(BANNER_PATH),
                caption=text_menu(),
                reply_markup=kb_menu_main()
            )
            await message.answer("Меню ниже 👇", reply_markup=reply_main())
            return
        except Exception:
            pass

    await message.answer(text_menu(), reply_markup=kb_menu_main())
    await message.answer("Меню ниже 👇", reply_markup=reply_main())


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Нет доступа.")
    await message.answer("⚙️ <b>Админ-панель Tinker VPN</b>\n<i>Управление заказами, пользователями и ключами</i>", reply_markup=kb_admin_menu())


@dp.message(F.text == "🛒 Купить")
async def buy_btn(message: Message):
    if db_is_banned(message.from_user.id):
        return await message.answer("⛔ Твой доступ к боту ограничен.")
    await message.answer(text_buy_intro(), reply_markup=kb_buy())


@dp.message(F.text == "🔑 Мои подписки")
async def my_subs_btn(message: Message):
    subs = db_get_accepted_subscriptions(message.from_user.id)
    await message.answer(text_subscription_card(message.from_user, subs), reply_markup=kb_sub_with_refresh(message.from_user.id))


@dp.message(F.text == "📢 Канал")
async def channel_btn(message: Message):
    await message.answer(f"📢 Канал: {TG_CHANNEL}")


@dp.message(F.text == "🆘 Поддержка")
async def support_btn(message: Message):
    await message.answer(f"🆘 Поддержка: {TG_CHANNEL}")


@dp.callback_query(F.data == "menu:main")
async def cb_menu_main(call: CallbackQuery):
    await call.answer()
    try:
        await call.message.edit_text(text_menu(), reply_markup=kb_menu_main())
    except TelegramBadRequest:
        await call.message.answer(text_menu(), reply_markup=kb_menu_main())


@dp.callback_query(F.data == "menu:buy")
async def cb_menu_buy(call: CallbackQuery):
    await call.answer()
    try:
        await call.message.edit_text(text_buy_intro(), reply_markup=kb_buy())
    except TelegramBadRequest:
        await call.message.answer(text_buy_intro(), reply_markup=kb_buy())


@dp.callback_query(F.data == "menu:subs")
async def cb_menu_subs(call: CallbackQuery):
    await call.answer()
    subs = db_get_accepted_subscriptions(call.from_user.id)
    text = text_subscription_card(call.from_user, subs)
    try:
        await call.message.edit_text(text, reply_markup=kb_sub_with_refresh(call.from_user.id))
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=kb_sub_with_refresh(call.from_user.id))


@dp.callback_query(F.data == "menu:cancel_order")
async def cancel_active_order(call: CallbackQuery):
    await call.answer()
    order = db_get_active_order(call.from_user.id)
    if not order:
        return await call.answer("Активного заказа нет", show_alert=True)

    db_set_status(order["id"], "cancelled")
    await call.message.answer("❌ Активный заказ отменён.", reply_markup=kb_menu_main())


@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy_plan(call: CallbackQuery):
    await call.answer()

    if db_is_banned(call.from_user.id):
        return await call.answer("Доступ ограничен", show_alert=True)

    plan = call.data.split(":")[1]
    if plan not in ("standard", "premium", "family"):
        return await call.answer("Неизвестный тариф", show_alert=True)

    active = db_get_active_order(call.from_user.id)
    if active:
        return await call.answer("У тебя уже есть активный заказ", show_alert=True)

    _, _, _, price = plan_meta(plan)
    order_id = db_create_order(call.from_user.id, call.from_user.username, plan, price)

    await call.message.answer(
        text_order_created(order_id, plan, price),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📎 Отправить чек сюда", callback_data=f"noop:{order_id}")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="menu:main")]
        ])
    )


@dp.callback_query(F.data.startswith("noop:"))
async def noop_call(call: CallbackQuery):
    await call.answer("Просто отправь чек следующим сообщением 👇", show_alert=True)


@dp.message(F.photo | F.document)
async def handle_receipt(message: Message):
    db_upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    if db_is_banned(message.from_user.id):
        return await message.answer("⛔ Твой доступ к боту ограничен.")

    order = db_get_active_order(message.from_user.id)
    if not order:
        return

    if order["status"] not in ("waiting_receipt", "pending_admin"):
        return

    db_set_status(order["id"], "pending_admin")
    db_set_payment_msg(order["id"], message.message_id)

    order = db_get_order(order["id"])

    try:
        if message.photo:
            sent = await bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=text_order_to_admin(order),
                reply_markup=kb_pending_admin(order["id"])
            )
        else:
            sent = await bot.send_document(
                ADMIN_ID,
                document=message.document.file_id,
                caption=text_order_to_admin(order),
                reply_markup=kb_pending_admin(order["id"])
            )

        db_set_admin_msg(order["id"], sent.message_id)
    except Exception as e:
        return await message.answer(f"❌ Не удалось отправить заявку админу: {html_escape(e)}")

    await message.answer(
        "✅ Чек отправлен на проверку.\n\n"
        "Ожидай подтверждения от администратора.",
        reply_markup=kb_menu_main()
    )


@dp.callback_query(F.data.startswith("sub:key:"))
async def cb_sub_key(call: CallbackQuery):
    await call.answer()
    plan = call.data.split(":")[2]
    subs = db_get_accepted_subscriptions(call.from_user.id)

    found = None
    for sub in subs:
        if sub["plan"] == plan:
            found = sub
            break

    if not found:
        return await call.answer("Подписка не найдена", show_alert=True)

    text = (
        f"{plan_visible_name(plan)}\n"
        f"{plan_conditions(plan)}\n\n"
        f"🔑 <b>Твой ключ:</b>\n<code>{html_escape(found['issued_key'] or '—')}</code>"
    )
    await call.message.answer(text, reply_markup=kb_sub_with_refresh(call.from_user.id))


@dp.callback_query(F.data == "sub:refresh")
async def cb_sub_refresh(call: CallbackQuery):
    await call.answer()

    subs = db_get_accepted_subscriptions(call.from_user.id)
    if not subs:
        return await call.answer("Нет активных подписок", show_alert=True)

    updated = 0
    for sub in subs:
        new_key = take_key(sub["plan"], sub.get("order_id") or 0)
        if new_key:
            updated += db_update_user_plan_key(call.from_user.id, sub["plan"], new_key)

    await call.message.answer(
        f"🔄 Обновление завершено.\nОбновлено подписок: <b>{updated}</b>",
        reply_markup=kb_sub_with_refresh(call.from_user.id)
    )


@dp.callback_query(F.data == "admin:home")
async def admin_home(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()
    try:
        await call.message.edit_text("⚙️ <b>Админ-панель Tinker VPN</b>\n<i>Управление заказами, пользователями и ключами</i>", reply_markup=kb_admin_menu())
    except TelegramBadRequest:
        await call.message.answer("⚙️ <b>Админ-панель Tinker VPN</b>\n<i>Управление заказами, пользователями и ключами</i>", reply_markup=kb_admin_menu())


@dp.callback_query(F.data == "admin:list")
async def admin_list(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()
    rows = db_list_pending()
    if not rows:
        return await call.message.answer("📦 Нет заявок на проверку.", reply_markup=kb_admin_menu())

    await call.message.answer("📦 <b>Заявки на проверку</b>", reply_markup=kb_admin_list(rows))


@dp.callback_query(F.data.startswith("admin:view:"))
async def admin_view_order(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    order_id = int(call.data.split(":")[2])
    order = db_get_order(order_id)
    if not order:
        return await call.answer("Заказ не найден", show_alert=True)

    uname = f"@{order['username']}" if order["username"] else "—"
    text = (
        "🧾 <b>Информация по заказу</b>\n\n"
        f"№: <code>#{order['id']}</code>\n"
        f"User ID: <code>{order['user_id']}</code>\n"
        f"Username: {html_escape(uname)}\n"
        f"Тариф: <b>{plan_visible_name(order['plan'])}</b>\n"
        f"Сумма: <b>{order['amount']}₽</b>\n"
        f"Статус: <b>{html_escape(order['status'])}</b>\n"
        f"Создан: <b>{format_ts(order['created_at'])}</b>\n"
        f"Подтверждён: <b>{format_ts(order['accepted_at'])}</b>\n"
        f"Ключ: <code>{html_escape(order['issued_key'] or '—')}</code>"
    )
    await call.message.answer(text, reply_markup=kb_admin_order(order["id"], order["user_id"]))


@dp.callback_query(F.data.startswith("admin:approve:"))
async def admin_approve(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    order_id = int(call.data.split(":")[2])
    order = db_get_order(order_id)
    if not order:
        return await call.answer("Заказ не найден", show_alert=True)

    if order["status"] == "accepted":
        return await call.answer("Уже подтверждено", show_alert=True)

    key = take_key(order["plan"], order_id)
    if not key:
        return await call.answer("Нет ключей для этого тарифа", show_alert=True)

    db_set_status(order_id, "accepted")
    db_set_issued(order_id, key)
    db_upsert_subscription(order["user_id"], order["plan"], key, order_id)

    user_text = (
        "✅ <b>Оплата подтверждена</b>\n\n"
        f"Тариф: <b>{plan_visible_name(order['plan'])}</b>\n"
        f"{plan_conditions(order['plan'])}\n\n"
        f"🔑 <b>Твой ключ:</b>\n<code>{html_escape(key)}</code>\n\n"
        "Чтобы посмотреть ключ позже — открой раздел <b>Мои подписки</b>."
    )

    try:
        await bot.send_message(order["user_id"], user_text, reply_markup=kb_sub_with_refresh(order["user_id"]))
    except TelegramForbiddenError:
        pass

    await call.message.answer(
        f"✅ Заказ <code>#{order_id}</code> подтверждён.\n"
        f"Выдан ключ:\n<code>{html_escape(key)}</code>",
        reply_markup=kb_admin_menu()
    )


@dp.callback_query(F.data.startswith("admin:reject:"))
async def admin_reject(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    order_id = int(call.data.split(":")[2])
    order = db_get_order(order_id)
    if not order:
        return await call.answer("Заказ не найден", show_alert=True)

    db_set_status(order_id, "cancelled")

    try:
        await bot.send_message(
            order["user_id"],
            "❌ Оплата не подтверждена.\n\nПроверь реквизиты и отправь новый чек.",
            reply_markup=kb_menu_main()
        )
    except TelegramForbiddenError:
        pass

    await call.message.answer(f"❌ Заказ <code>#{order_id}</code> отклонён.", reply_markup=kb_admin_menu())


@dp.callback_query(F.data == "admin:search")
async def admin_search_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    await state.set_state(AdminStates.search_wait)
    await call.message.answer(
        "🔎 Введи номер заказа, user_id, username, тариф или статус.\n\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.message(AdminStates.search_wait)
async def admin_search_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    q = (message.text or "").strip()
    if q.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Поиск отменён.", reply_markup=kb_admin_menu())

    rows = db_search_orders(q, 20)
    await state.clear()

    if not rows:
        return await message.answer("Ничего не найдено.", reply_markup=kb_admin_menu())

    keyboard = []
    for oid, uid, uname, plan, amount, status, created_at, accepted_at in rows:
        u = f"@{uname}" if uname else str(uid)
        badge = "📦" if plan == "standard" else "⚡" if plan == "premium" else "👨‍👩‍👧‍👦"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{badge} #{oid} • {status} • {u}",
                callback_data=f"admin:view:{oid}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")])

    await message.answer("🔎 <b>Результаты поиска</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@dp.callback_query(F.data.startswith("admin:users:"))
async def admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    offset = int(call.data.split(":")[2])
    rows = db_list_users(offset, USERS_PAGE_SIZE)
    total = db_count_users()

    stats = db_users_stats()
    lines = [
        "👥 <b>Пользователи</b>",
        "Нажми на пользователя ниже, чтобы открыть карточку.",
        "",
        f"Всего: <b>{stats['total']}</b>",
        f"Активны 24ч: <b>{stats['active_24h']}</b>",
        f"Активны 7д: <b>{stats['active_7d']}</b>",
        f"Банов: <b>{stats['banned']}</b>",
        "",
    ]

    if not rows:
        lines.append("Список пуст.")
    else:
        for uid, username, first_name, last_seen, is_blocked, is_banned in rows:
            uname = f"@{username}" if username else "—"
            ban_mark = " ⛔" if is_banned else ""
            lines.append(
                f"• <code>{uid}</code> {html_escape(first_name or '—')} {html_escape(uname)} "
                f"— {format_ts(last_seen)}{ban_mark}"
            )

    text = "\n".join(lines)
    keyboard = kb_admin_users_page(offset, total, rows, banned=False)

    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("admin:usercard:"))
async def admin_user_card(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    user_id = int(call.data.split(":")[2])
    user = db_get_user(user_id)
    if not user:
        return await call.answer("Пользователь не найден", show_alert=True)

    text = text_admin_user_card(user_id)
    keyboard = kb_admin_user_actions(user_id, bool(user["is_banned"]))

    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("admin:banned:"))
async def admin_banned(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    offset = int(call.data.split(":")[2])
    rows = db_list_banned_users(offset, USERS_PAGE_SIZE)
    total = db_count_banned_users()

    lines = ["⛔ <b>Забаненные пользователи</b>", "Нажми на пользователя ниже, чтобы открыть карточку.", ""]
    if not rows:
        lines.append("Список пуст.")
    else:
        for uid, username, first_name, last_seen, is_blocked, is_banned in rows:
            uname = f"@{username}" if username else "—"
            lines.append(f"• <code>{uid}</code> {html_escape(first_name or '—')} {html_escape(uname)}")

    try:
        await call.message.edit_text("\n".join(lines), reply_markup=kb_admin_users_page(offset, total, rows, banned=True))
    except TelegramBadRequest:
        await call.message.answer("\n".join(lines), reply_markup=kb_admin_users_page(offset, total, rows, banned=True))


@dp.message(Command("user"))
async def admin_user_quick(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("Использование: <code>/user USER_ID</code>")
    uid = int(parts[1])
    user = db_get_user(uid)
    if not user:
        return await message.answer("Пользователь не найден.")

    text = text_admin_user_card(uid)
    await message.answer(text, reply_markup=kb_admin_user_actions(uid, bool(user["is_banned"])))


@dp.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()

    user_id = int(call.data.split(":")[2])
    db_ban_user_and_revoke(user_id)

    try:
        await bot.send_message(user_id, "⛔ Твой доступ к Tinker VPN ограничен.")
    except Exception:
        pass

    await call.message.answer(f"⛔ Пользователь <code>{user_id}</code> забанен.", reply_markup=kb_admin_menu())


@dp.callback_query(F.data.startswith("admin:unban:"))
async def admin_unban(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()

    user_id = int(call.data.split(":")[2])
    db_unban_user(user_id)

    try:
        await bot.send_message(user_id, "✅ Доступ к Tinker VPN восстановлен.")
    except Exception:
        pass

    await call.message.answer(f"✅ Пользователь <code>{user_id}</code> разбанен.", reply_markup=kb_admin_menu())


@dp.callback_query(F.data.startswith("admin:issue:"))
async def admin_issue_plan(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    parts = call.data.split(":")
    user_id = int(parts[2])
    plan = parts[3]

    if plan not in ("standard", "premium", "family"):
        return await call.answer("Неизвестный тариф", show_alert=True)

    ok, result = admin_issue_subscription(user_id, plan)
    if not ok:
        return await call.answer(result, show_alert=True)

    try:
        await bot.send_message(
            user_id,
            "🎁 <b>Тебе выдана подписка вручную</b>\n\n"
            f"Тариф: <b>{plan_visible_name(plan)}</b>\n"
            f"{plan_conditions(plan)}\n\n"
            f"🔑 <b>Твой ключ:</b>\n<code>{html_escape(result)}</code>",
            reply_markup=kb_sub_with_refresh(user_id)
        )
    except Exception:
        pass

    user = db_get_user(user_id)
    text = text_admin_user_card(user_id)
    keyboard = kb_admin_user_actions(user_id, bool(user and user["is_banned"]))
    await call.message.answer(
        f"✅ Подписка {plan_visible_name(plan)} выдана пользователю <code>{user_id}</code>.\n"
        f"Ключ:\n<code>{html_escape(result)}</code>"
    )
    await call.message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("msguser:"))
async def admin_write_user_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    user_id = int(call.data.split(":")[1])
    await state.update_data(target_user=user_id)
    await state.set_state(AdminStates.message_user_wait)

    await call.message.answer(
        f"✉️ Введи сообщение для отправки пользователю <code>{user_id}</code>.\n\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.message(AdminStates.message_user_wait)
async def admin_send_user_final(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if message.text and message.text.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Отправка отменена.", reply_markup=kb_admin_menu())

    data = await state.get_data()
    uid = data.get("target_user")
    if not uid:
        await state.clear()
        return await message.answer("❌ Пользователь не найден.", reply_markup=kb_admin_menu())

    try:
        await bot.send_message(uid, "🔔 <b>Сообщение от администрации Tinker VPN:</b>")
        await message.copy_to(uid)
        await message.answer(f"✅ Сообщение отправлено пользователю <code>{uid}</code>.", reply_markup=kb_admin_menu())
    except TelegramForbiddenError:
        await message.answer(f"❌ Пользователь <code>{uid}</code> заблокировал бота.", reply_markup=kb_admin_menu())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {html_escape(e)}", reply_markup=kb_admin_menu())
    finally:
        await state.clear()


@dp.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)
    await call.answer()
    await state.set_state(AdminStates.broadcast_wait)
    await call.message.answer(
        "📢 Отправь сообщение для рассылки.\n\n"
        "Поддерживается текст, фото, видео, документ.\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.message(AdminStates.broadcast_wait)
async def admin_broadcast_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if message.text and message.text.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Рассылка отменена.", reply_markup=kb_admin_menu())

    rows = db_list_users(0, 100000)
    ok = 0
    bad = 0

    for uid, username, first_name, last_seen, is_blocked, is_banned in rows:
        if is_banned:
            continue
        try:
            await message.copy_to(uid)
            ok += 1
        except Exception:
            bad += 1

    await state.clear()
    await message.answer(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"📬 Успешно: <b>{ok}</b>\n"
        f"🚫 Ошибки: <b>{bad}</b>",
        reply_markup=kb_admin_menu()
    )


@dp.callback_query(F.data == "admin:keys")
async def admin_keys(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    text = (
        "🔑 <b>Ключи</b>\n\n"
        f"📦 Standart: <b>{db_keys_count('standard')}</b>\n"
        f"⚡ Premium: <b>{db_keys_count('premium')}</b>\n"
        f"👨‍👩‍👧‍👦 Family: <b>{db_keys_count('family')}</b>\n\n"
        "Добавление — по одному или по несколько, каждый ключ с новой строки."
    )
    await call.message.answer(text, reply_markup=kb_admin_keys())


@dp.callback_query(F.data.startswith("admin:keyclear:"))
async def admin_key_clear(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    plan = call.data.split(":")[2]
    count_before = db_keys_count(plan)
    db_keys_clear(plan)
    await call.answer("Ключи очищены", show_alert=True)
    await call.message.answer(
        f"🧹 Для тарифа {plan_visible_name(plan)} очищено ключей: <b>{count_before}</b>",
        reply_markup=kb_admin_keys()
    )


@dp.callback_query(F.data.startswith("admin:keydelete:"))
async def admin_key_delete_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    plan = call.data.split(":")[2]
    await call.answer()
    await state.update_data(key_delete_plan=plan)
    await state.set_state(AdminStates.key_delete_wait)
    await call.message.answer(
        f"🗑 Отправь <b>точный текст ключа</b> для удаления из тарифа {plan_visible_name(plan)}.\n\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.callback_query(F.data.startswith("admin:keyadd:"))
async def admin_key_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    plan = call.data.split(":")[2]
    await call.answer()
    await state.update_data(key_plan=plan)
    await state.set_state(AdminStates.keys_wait)
    await call.message.answer(
        f"🔑 Отправь ключи для тарифа <b>{plan_visible_name(plan)}</b>.\n"
        "Каждый ключ — с новой строки.\n\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.message(AdminStates.keys_wait)
async def admin_key_add_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        return await message.answer("Нужен текст с ключами.")
    if message.text.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Добавление ключей отменено.", reply_markup=kb_admin_menu())

    data = await state.get_data()
    plan = data.get("key_plan")
    keys = [x.strip() for x in message.text.splitlines() if x.strip()]

    added, skipped = db_keys_add(plan, keys)
    await state.clear()
    await message.answer(
        f"✅ Для тарифа {plan_visible_name(plan)}\n"
        f"Добавлено: <b>{added}</b>\n"
        f"Пропущено дублей: <b>{skipped}</b>",
        reply_markup=kb_admin_menu()
    )


@dp.message(AdminStates.key_delete_wait)
async def admin_key_delete_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    key_text = (message.text or "").strip()
    if key_text.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Удаление ключа отменено.", reply_markup=kb_admin_menu())

    if not key_text:
        return await message.answer("Пришли точный ключ текстом.")

    data = await state.get_data()
    plan = data.get("key_delete_plan")
    deleted = db_keys_delete_exact(plan, key_text)
    await state.clear()

    if not deleted:
        return await message.answer(
            f"❌ Ключ для тарифа {plan_visible_name(plan)} не найден.",
            reply_markup=kb_admin_menu()
        )

    await message.answer(
        f"✅ Ключ удалён из тарифа {plan_visible_name(plan)}.",
        reply_markup=kb_admin_menu()
    )


@dp.callback_query(F.data == "admin:prices")
async def admin_prices(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    await call.answer()
    text = (
        "🏷 <b>Цены</b>\n\n"
        f"📦 Standart: <b>{db_settings_get('price_standard', '75')}₽</b>\n"
        f"⚡ Premium: <b>{db_settings_get('price_premium', '300')}₽</b>\n"
        f"👨‍👩‍👧‍👦 Family: <b>{db_settings_get('price_family', '150')}₽</b>"
    )
    await call.message.answer(text, reply_markup=kb_admin_prices())


@dp.callback_query(F.data.startswith("admin:price:"))
async def admin_price_edit_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer("Нет доступа", show_alert=True)

    plan = call.data.split(":")[2]
    await call.answer()
    await state.update_data(price_plan=plan)
    await state.set_state(AdminStates.price_wait)
    await call.message.answer(
        f"✏️ Введи новую цену для тарифа {plan_visible_name(plan)}.\n\n"
        "Для отмены напиши: <code>отмена</code>"
    )


@dp.message(AdminStates.price_wait)
async def admin_price_edit_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    text = (message.text or "").strip()
    if text.lower() == "отмена":
        await state.clear()
        return await message.answer("❌ Изменение цены отменено.", reply_markup=kb_admin_menu())

    if not text.isdigit():
        return await message.answer("Нужна цена числом.")

    data = await state.get_data()
    plan = data.get("price_plan")
    key_name = {
        "standard": "price_standard",
        "premium": "price_premium",
        "family": "price_family",
    }[plan]

    db_settings_set(key_name, text)
    await state.clear()
    await message.answer(
        f"✅ Цена для {plan_visible_name(plan)} изменена на <b>{int(text)}₽</b>",
        reply_markup=kb_admin_menu()
    )


@dp.message(F.text)
async def text_fallback(message: Message):
    db_upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    order = db_get_active_order(message.from_user.id)
    if order and not is_admin(message.from_user.id):
        return await message.answer(
            "📎 У тебя есть активный заказ.\n"
            "Отправь сюда фото или файл с чеком / скрином оплаты."
        )

    if message.text == "/start":
        return

    await message.answer("Выбери действие ниже 👇", reply_markup=reply_main())


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if ADMIN_ID == 0:
        raise RuntimeError("ADMIN_ID is not set")

    db_init()
    import_keys_from_files_if_empty()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
