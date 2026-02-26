"""
╔═══════════════════════════════════════════════════════════╗
║  🌟 APON HOSTING PANEL — Premium Edition v4.0 🌟         ║
║  Developer: @developer_apon                               ║
║  All bugs fixed, optimized & stable                       ║
╚═══════════════════════════════════════════════════════════╝
"""

import telebot, subprocess, os, zipfile, tempfile, shutil, time, psutil
import sqlite3, json, logging, signal, threading, re, sys, atexit
import requests, random, hashlib, string, traceback
from telebot import types
from datetime import datetime, timedelta
from flask import Flask, jsonify
from threading import Thread
from collections import defaultdict

# ═══════════════════════════════════════════════════
#  FLASK KEEP-ALIVE
# ═══════════════════════════════════════════════════
flask_app = Flask('AponHosting')

@flask_app.route('/')
def flask_home():
    return "<h1>🌟 APON HOSTING PANEL 🌟</h1><p>Status: ✅ Online</p>"

@flask_app.route('/health')
def flask_health():
    return jsonify({"status": "ok", "uptime": get_uptime(), "v": "4.0"})

def keep_alive():
    Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()

# ═══════════════════════════════════════════════════
#  BRANDING
# ═══════════════════════════════════════════════════
BRAND = "🌟 APON HOSTING PANEL"
BRAND_SHORT = "AHP"
BRAND_VER = "v4.0"
BRAND_TAG = f"{BRAND} {BRAND_VER}"

# ═══════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════
TOKEN = '8258702948:AAHCT3iI934w6MnLle72GPUxQTR2O3z6aWA'
OWNER_ID = 6678577936
ADMIN_ID = 6678577936
BOT_USERNAME = 'apon_vps_bot'
YOUR_USERNAME = '@developer_apon'
UPDATE_CHANNEL = 'https://t.me/developer_apon_07'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload_bots')
DATA_DIR = os.path.join(BASE_DIR, 'apon_data')
DB_PATH = os.path.join(DATA_DIR, 'apon.db')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

DEFAULT_FORCE_CHANNELS = {'developer_apon_07': 'Developer Apon Updates'}
FORCE_SUB_ENABLED = True

PLAN_LIMITS = {
    'free':      {'name': '🆓 Free',       'max_bots': 1,  'ram': 128,  'auto_restart': False, 'price': 0},
    'starter':   {'name': '🟢 Starter',    'max_bots': 2,  'ram': 256,  'auto_restart': True,  'price': 99},
    'basic':     {'name': '⭐ Basic',       'max_bots': 5,  'ram': 512,  'auto_restart': True,  'price': 199},
    'pro':       {'name': '💎 Pro',         'max_bots': 15, 'ram': 2048, 'auto_restart': True,  'price': 499},
    'enterprise':{'name': '🏢 Enterprise',  'max_bots': 50, 'ram': 4096, 'auto_restart': True,  'price': 999},
    'lifetime':  {'name': '👑 Lifetime',    'max_bots': -1, 'ram': 8192, 'auto_restart': True,  'price': 1999},
}

PAYMENT_METHODS = {
    'bkash':   {'name': 'bKash',       'number': '01306633616',           'type': 'Send Money',      'icon': '🟪'},
    'nagad':   {'name': 'Nagad',       'number': '01306633616',           'type': 'Send Money',      'icon': '🟧'},
    'rocket':  {'name': 'Rocket',      'number': '01306633616',           'type': 'Send Money',      'icon': '🟦'},
    'upay':    {'name': 'Upay',        'number': '01306633616',           'type': 'Send Money',      'icon': '🟩'},
    'binance': {'name': 'Binance Pay', 'number': 'Binance ID: 758637628','type': 'Binance Pay/USDT','icon': '🟡'},
    'bank':    {'name': 'Bank',        'number': 'Contact Admin',         'type': 'Transfer',        'icon': '🏦'},
}

REF_BONUS_DAYS = 3
REF_COMMISSION = 20

MODULES_MAP = {
    'telebot': 'pytelegrambotapi', 'telegram': 'python-telegram-bot', 'pyrogram': 'pyrogram',
    'telethon': 'telethon', 'aiogram': 'aiogram', 'PIL': 'Pillow', 'cv2': 'opencv-python',
    'sklearn': 'scikit-learn', 'bs4': 'beautifulsoup4', 'dotenv': 'python-dotenv',
    'yaml': 'pyyaml', 'aiohttp': 'aiohttp', 'numpy': 'numpy', 'pandas': 'pandas',
    'requests': 'requests', 'flask': 'flask', 'fastapi': 'fastapi', 'motor': 'motor',
    'pymongo': 'pymongo', 'httpx': 'httpx', 'cryptography': 'cryptography',
}

for _d in [UPLOAD_DIR, DATA_DIR, LOGS_DIR, BACKUP_DIR]:
    os.makedirs(_d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s|%(name)s|%(levelname)s|%(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'apon.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('APON')

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

bot_scripts = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
bot_start_time = datetime.now()
user_states = {}
payment_states = {}
user_msg_times = defaultdict(list)

# ═══════════════════════════════════════════════════
#  SAFE MESSAGE SENDER (Error Fix)
# ═══════════════════════════════════════════════════
def safe_send(chat_id, text, **kwargs):
    """Send message with error handling"""
    try:
        kwargs.setdefault('parse_mode', 'HTML')
        return bot.send_message(chat_id, text, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        logger.warning(f"API Error sending to {chat_id}: {e}")
        # Try without parse_mode if HTML error
        if 'can\'t parse' in str(e).lower() or 'bad request' in str(e).lower():
            try:
                kwargs.pop('parse_mode', None)
                return bot.send_message(chat_id, text, **kwargs)
            except:
                pass
        return None
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def safe_edit(text, chat_id, msg_id, **kwargs):
    """Edit message with error handling"""
    try:
        kwargs.setdefault('parse_mode', 'HTML')
        return bot.edit_message_text(text, chat_id, msg_id, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        err = str(e).lower()
        if 'message is not modified' in err:
            return None
        if 'can\'t parse' in err or 'bad request' in err:
            try:
                kwargs.pop('parse_mode', None)
                return bot.edit_message_text(text, chat_id, msg_id, **kwargs)
            except:
                pass
        logger.warning(f"Edit error: {e}")
        return None
    except Exception as e:
        logger.error(f"Edit error: {e}")
        return None

def safe_answer(call_id, text="", **kwargs):
    """Answer callback with error handling"""
    try:
        bot.answer_callback_query(call_id, text, **kwargs)
    except:
        pass

# ═══════════════════════════════════════════════════
#  RATE LIMITER
# ═══════════════════════════════════════════════════
def rate_check(uid):
    now = time.time()
    user_msg_times[uid] = [t for t in user_msg_times[uid] if now - t < 60]
    if len(user_msg_times[uid]) >= 30:
        return False
    if user_msg_times[uid] and now - user_msg_times[uid][-1] < 0.5:
        return False
    user_msg_times[uid].append(now)
    return True

# ═══════════════════════════════════════════════════
#  SIMPLE ANIMATIONS (Less API calls = No Rate Limit)
# ═══════════════════════════════════════════════════
def loading_msg(cid, final_text, atype="loading"):
    """Simple 2-step animation instead of 6 steps"""
    try:
        icons = {
            "loading": "⏳", "upload": "📤", "run": "🚀",
            "stop": "🛑", "install": "📦", "verify": "🔍", "pay": "💳"
        }
        icon = icons.get(atype, "⏳")
        msg = bot.send_message(cid, f"{icon} Processing...")
        time.sleep(1)
        safe_edit(final_text, cid, msg.message_id)
        return msg
    except:
        return safe_send(cid, final_text)

def progress_msg(cid, text):
    """Simple progress"""
    try:
        msg = bot.send_message(cid, f"⏳ {text}...")
        time.sleep(0.5)
        return msg
    except:
        return None

# ═══════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════
def get_uptime():
    d = datetime.now() - bot_start_time
    h, r = divmod(d.seconds, 3600)
    m, s = divmod(r, 60)
    p = []
    if d.days:
        p.append(f"{d.days}d")
    if h:
        p.append(f"{h}h")
    p.append(f"{m}m {s}s")
    return " ".join(p)

def fmt_size(b):
    for u in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"

def gen_ref_code(uid):
    uid = int(uid)
    chars = string.digits + string.ascii_uppercase
    enc = ''
    t = uid
    if t == 0:
        enc = '0'
    else:
        while t > 0:
            enc = chars[t % 36] + enc
            t //= 36
    salt = hashlib.md5(f"{uid}_apon_hosting".encode()).hexdigest()[:2].upper()
    return f"AHP{enc}{salt}"

def time_left(e):
    if not e:
        return "♾️ Lifetime"
    try:
        end = datetime.fromisoformat(e)
        if end <= datetime.now():
            return "❌ Expired"
        d = end - datetime.now()
        if d.days > 0:
            return f"{d.days}d {d.seconds // 3600}h"
        return f"{d.seconds // 3600}h {(d.seconds % 3600) // 60}m"
    except:
        return "?"

def user_folder(uid):
    f = os.path.join(UPLOAD_DIR, str(uid))
    os.makedirs(f, exist_ok=True)
    return f

def is_running(sk):
    i = bot_scripts.get(sk)
    if i and i.get('process'):
        try:
            p = psutil.Process(i['process'].pid)
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except:
            return False
    return False

def bot_running(uid, name):
    return is_running(f"{uid}_{name}")

def cleanup(sk):
    if sk in bot_scripts:
        i = bot_scripts[sk]
        try:
            lf = i.get('log_file')
            if lf and hasattr(lf, 'close') and not lf.closed:
                lf.close()
        except:
            pass
        del bot_scripts[sk]

def kill_tree(pi):
    try:
        try:
            lf = pi.get('log_file')
            if lf and hasattr(lf, 'close') and not lf.closed:
                lf.close()
        except:
            pass
        p = pi.get('process')
        if p and hasattr(p, 'pid'):
            try:
                par = psutil.Process(p.pid)
                ch = par.children(recursive=True)
                for c in ch:
                    try:
                        c.terminate()
                    except:
                        pass
                psutil.wait_procs(ch, timeout=3)
                for c in ch:
                    try:
                        c.kill()
                    except:
                        pass
                try:
                    par.terminate()
                    par.wait(3)
                except psutil.TimeoutExpired:
                    par.kill()
                except psutil.NoSuchProcess:
                    pass
            except psutil.NoSuchProcess:
                pass
    except:
        pass

def sys_stats():
    try:
        c = psutil.cpu_percent(interval=1)
        m = psutil.virtual_memory()
        d = psutil.disk_usage('/')
        return {
            'cpu': c, 'mem': m.percent,
            'disk': round(d.used / d.total * 100, 1),
            'up': get_uptime(),
            'mem_total': fmt_size(m.total),
            'disk_total': fmt_size(d.total)
        }
    except:
        return {'cpu': 0, 'mem': 0, 'disk': 0, 'up': get_uptime(), 'mem_total': '?', 'disk_total': '?'}

def bot_res(sk):
    i = bot_scripts.get(sk)
    if not i or not i.get('process'):
        return 0, 0
    try:
        p = psutil.Process(i['process'].pid)
        return round(p.memory_info().rss / (1024 ** 2), 1), round(p.cpu_percent(0.3), 1)
    except:
        return 0, 0

# ═══════════════════════════════════════════════════
#  FORCE SUBSCRIBE
# ═══════════════════════════════════════════════════
def check_joined(uid):
    if not FORCE_SUB_ENABLED:
        return True, []
    if uid == OWNER_ID or uid in admin_ids:
        return True, []
    channels = db.get_active_channels()
    if not channels:
        ch_list = [(u, n) for u, n in DEFAULT_FORCE_CHANNELS.items()]
    else:
        ch_list = [(c['channel_username'], c['channel_name']) for c in channels]
    not_joined = []
    for cu, cn in ch_list:
        try:
            mem = bot.get_chat_member(f"@{cu}", uid)
            if mem.status in ['left', 'kicked']:
                not_joined.append((cu, cn))
        except telebot.apihelper.ApiTelegramException:
            not_joined.append((cu, cn))
        except:
            continue
    return len(not_joined) == 0, not_joined

def force_sub_kb(not_joined):
    m = types.InlineKeyboardMarkup(row_width=1)
    for cu, cn in not_joined:
        m.add(types.InlineKeyboardButton(f"📢 Join {cn}", url=f"https://t.me/{cu}"))
    m.add(types.InlineKeyboardButton("✅ Verify Joined", callback_data="verify_join"))
    return m

def send_force_sub(cid, nj):
    ch = ""
    for i, (cu, cn) in enumerate(nj, 1):
        ch += f"  {i}. {cn} — @{cu}\n"
    safe_send(cid,
        f"🔒 <b>CHANNEL VERIFICATION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Join our channels to continue!\n\n"
        f"{ch}\n"
        f"👇 Join all, then press Verify\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=force_sub_kb(nj))

# ═══════════════════════════════════════════════════
#  SMART ENTRY DETECTOR
# ═══════════════════════════════════════════════════
class Detector:
    PY = ['main.py', 'app.py', 'bot.py', 'run.py', 'start.py', 'server.py', 'index.py', '__main__.py']
    JS = ['index.js', 'app.js', 'bot.js', 'main.js', 'server.js', 'start.js', 'run.js']

    @staticmethod
    def detect(d):
        if not os.path.isdir(d):
            if os.path.isfile(d):
                return os.path.basename(d), d.rsplit('.', 1)[-1].lower(), 'exact'
            return None, None, None

        top = os.listdir(d)
        for e in Detector.PY:
            if e in top and os.path.isfile(os.path.join(d, e)):
                return e, 'py', 'high'
        for e in Detector.JS:
            if e in top and os.path.isfile(os.path.join(d, e)):
                return e, 'js', 'high'

        pj = os.path.join(d, 'package.json')
        if os.path.exists(pj):
            try:
                with open(pj) as f:
                    pkg = json.load(f)
                if 'main' in pkg and os.path.exists(os.path.join(d, pkg['main'])):
                    return pkg['main'], pkg['main'].rsplit('.', 1)[-1].lower(), 'high'
                if 'scripts' in pkg and 'start' in pkg['scripts']:
                    cmd = pkg['scripts']['start']
                    m = re.search(r'node\s+(\S+\.js)', cmd)
                    if m and os.path.exists(os.path.join(d, m.group(1))):
                        return m.group(1), 'js', 'high'
                    m = re.search(r'python[3]?\s+(\S+\.py)', cmd)
                    if m and os.path.exists(os.path.join(d, m.group(1))):
                        return m.group(1), 'py', 'high'
            except:
                pass

        pf = os.path.join(d, 'Procfile')
        if os.path.exists(pf):
            try:
                with open(pf) as f:
                    c = f.read()
                m = re.search(r'(?:worker|web):\s*python[3]?\s+(\S+\.py)', c)
                if m and os.path.exists(os.path.join(d, m.group(1))):
                    return m.group(1), 'py', 'high'
                m = re.search(r'(?:worker|web):\s*node\s+(\S+\.js)', c)
                if m and os.path.exists(os.path.join(d, m.group(1))):
                    return m.group(1), 'js', 'high'
            except:
                pass

        for root, dirs, files in os.walk(d):
            if os.path.relpath(root, d).count(os.sep) > 1:
                continue
            for e in Detector.PY:
                if e in files:
                    return os.path.relpath(os.path.join(root, e), d), 'py', 'medium'
            for e in Detector.JS:
                if e in files:
                    return os.path.relpath(os.path.join(root, e), d), 'js', 'medium'

        pyf, jsf = [], []
        for root, dirs, files in os.walk(d):
            if os.path.relpath(root, d).count(os.sep) > 1:
                continue
            for f in files:
                fp = os.path.join(root, f)
                rp = os.path.relpath(fp, d)
                if f.endswith('.py'):
                    pyf.append((rp, fp))
                elif f.endswith('.js'):
                    jsf.append((rp, fp))

        pi = ['infinity_polling', 'polling()', 'bot.polling', 'app.run(', 'if __name__', 'telebot.TeleBot', 'Bot(token']
        for rp, fp in pyf:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    c = f.read(5000)
                if sum(1 for x in pi if x in c) >= 2:
                    return rp, 'py', 'medium'
            except:
                pass

        ji = ['require(', 'app.listen', 'bot.launch', 'client.login', 'express()']
        for rp, fp in jsf:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    c = f.read(5000)
                if sum(1 for x in ji if x in c) >= 2:
                    return rp, 'js', 'medium'
            except:
                pass

        if pyf:
            return pyf[0][0], 'py', 'low'
        if jsf:
            return jsf[0][0], 'js', 'low'
        return None, None, None

    @staticmethod
    def install_req(d, cid=None):
        r = os.path.join(d, 'requirements.txt')
        if os.path.exists(r):
            if cid:
                safe_send(cid, "📦 Installing requirements...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', r, '--quiet'],
                               capture_output=True, text=True, timeout=300, cwd=d)
            except:
                pass
        return True

    @staticmethod
    def install_npm(d, cid=None):
        if os.path.exists(os.path.join(d, 'package.json')) and not os.path.exists(os.path.join(d, 'node_modules')):
            if cid:
                safe_send(cid, "📦 npm install...")
            try:
                subprocess.run(['npm', 'install', '--production'],
                               capture_output=True, text=True, timeout=300, cwd=d)
            except:
                pass
        return True

    @staticmethod
    def report(d):
        e, ft, cf = Detector.detect(d)
        if not e:
            return None, None, "❌ No runnable file!"
        ci = {'exact': '🎯 Exact', 'high': '✅ High', 'medium': '🟡 Medium', 'low': '⚠️ Low'}
        ti = {'py': '🐍 Python', 'js': '🟨 Node.js'}
        return e, ft, f"📄 Entry: {e}\n🔤 Type: {ti.get(ft, ft)}\n🎯 Confidence: {ci.get(cf, cf)}"

det = Detector()

# ═══════════════════════════════════════════════════
#  DATABASE (ALL TABLES FIXED)
# ═══════════════════════════════════════════════════
class DB:
    _lock = threading.Lock()

    def __init__(self):
        self.path = DB_PATH
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def exe(self, q, p=(), fetch=False, one=False):
        with self._lock:
            c = self._conn()
            cur = c.cursor()
            try:
                cur.execute(q, p)
                if fetch:
                    r = [dict(x) for x in cur.fetchall()]
                    c.close()
                    return r
                if one:
                    x = cur.fetchone()
                    c.close()
                    return dict(x) if x else None
                c.commit()
                lid = cur.lastrowid
                c.close()
                return lid
            except Exception as e:
                c.close()
                logger.error(f"DB: {e}")
                return None

    def _init(self):
        # Users table
        self.exe("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            plan TEXT DEFAULT 'free',
            subscription_end TEXT,
            is_lifetime INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            wallet_balance REAL DEFAULT 0.0,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0,
            referral_level TEXT DEFAULT 'bronze',
            referral_earnings REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            created_at TEXT DEFAULT(datetime('now')),
            last_active TEXT DEFAULT(datetime('now'))
        )""")

        # Bots table
        self.exe("""CREATE TABLE IF NOT EXISTS bots(
            bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_name TEXT NOT NULL,
            bot_token TEXT DEFAULT '',
            file_path TEXT NOT NULL,
            entry_file TEXT DEFAULT 'main.py',
            file_type TEXT DEFAULT 'py',
            status TEXT DEFAULT 'stopped',
            pid INTEGER,
            restarts_today INTEGER DEFAULT 0,
            total_restarts INTEGER DEFAULT 0,
            auto_restart INTEGER DEFAULT 1,
            last_started TEXT,
            last_stopped TEXT,
            last_crash TEXT,
            error_log TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            detection_confidence TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Payments table
        self.exe("""CREATE TABLE IF NOT EXISTS payments(
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            duration_days INTEGER DEFAULT 30,
            status TEXT DEFAULT 'pending',
            approved_by INTEGER,
            created_at TEXT DEFAULT(datetime('now')),
            processed_at TEXT
        )""")

        # Referrals table
        self.exe("""CREATE TABLE IF NOT EXISTS referrals(
            ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            bonus_days INTEGER DEFAULT 0,
            commission REAL DEFAULT 0,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Wallet transactions
        self.exe("""CREATE TABLE IF NOT EXISTS wallet_tx(
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tx_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Admin logs
        self.exe("""CREATE TABLE IF NOT EXISTS admin_logs(
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user INTEGER,
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Force channels
        self.exe("""CREATE TABLE IF NOT EXISTS force_channels(
            channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE NOT NULL,
            channel_name TEXT DEFAULT '',
            added_by INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # Tickets
        self.exe("""CREATE TABLE IF NOT EXISTS tickets(
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            admin_reply TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # ✅ NOTIFICATIONS TABLE (WAS MISSING - FIXED!)
        self.exe("""CREATE TABLE IF NOT EXISTS notifications(
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Notification',
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        # ✅ PROMO CODES TABLE (WAS MISSING - FIXED!)
        self.exe("""CREATE TABLE IF NOT EXISTS promo_codes(
            promo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_pct INTEGER DEFAULT 10,
            max_uses INTEGER DEFAULT 100,
            used_count INTEGER DEFAULT 0,
            created_by INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        logger.info("✅ All DB tables ready")

    # ── Users ──
    def get_user(self, uid):
        return self.exe("SELECT * FROM users WHERE user_id=?", (uid,), one=True)

    def create_user(self, uid, un='', fn='', rc='', rb=None):
        self.exe("INSERT OR IGNORE INTO users(user_id,username,full_name,referral_code,referred_by) VALUES(?,?,?,?,?)",
                 (uid, un, fn, rc, rb))

    def update_user(self, uid, **kw):
        if not kw:
            return
        self.exe(f"UPDATE users SET {','.join(f'{k}=?' for k in kw)} WHERE user_id=?",
                 list(kw.values()) + [uid])

    def get_all_users(self):
        return self.exe("SELECT * FROM users", fetch=True) or []

    def ban(self, uid, r=''):
        self.update_user(uid, is_banned=1, ban_reason=r)

    def unban(self, uid):
        self.update_user(uid, is_banned=0, ban_reason='')

    def set_sub(self, uid, plan, days=30):
        if plan == 'lifetime':
            self.update_user(uid, plan=plan, is_lifetime=1, subscription_end=None)
        else:
            self.update_user(uid, plan=plan, is_lifetime=0,
                             subscription_end=(datetime.now() + timedelta(days=days)).isoformat())

    def rem_sub(self, uid):
        self.update_user(uid, plan='free', is_lifetime=0, subscription_end=None)

    def is_active(self, uid):
        u = self.get_user(uid)
        if not u:
            return False
        if u['is_lifetime'] or u['plan'] == 'free':
            return True
        if u['subscription_end']:
            try:
                return datetime.fromisoformat(u['subscription_end']) > datetime.now()
            except:
                return False
        return False

    def get_plan(self, uid):
        u = self.get_user(uid)
        if not u:
            return PLAN_LIMITS['free']
        if uid == OWNER_ID or uid in admin_ids:
            return PLAN_LIMITS['lifetime']
        return PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])

    # ── Bots ──
    def add_bot(self, uid, name, path, entry='main.py', ft='py', tok='', sz=0, conf=''):
        return self.exe(
            "INSERT INTO bots(user_id,bot_name,file_path,entry_file,file_type,bot_token,file_size,detection_confidence) VALUES(?,?,?,?,?,?,?,?)",
            (uid, name, path, entry, ft, tok, sz, conf))

    def get_bots(self, uid):
        return self.exe("SELECT * FROM bots WHERE user_id=?", (uid,), fetch=True) or []

    def get_bot(self, bid):
        return self.exe("SELECT * FROM bots WHERE bot_id=?", (bid,), one=True)

    def update_bot(self, bid, **kw):
        if not kw:
            return
        self.exe(f"UPDATE bots SET {','.join(f'{k}=?' for k in kw)} WHERE bot_id=?",
                 list(kw.values()) + [bid])

    def del_bot(self, bid):
        self.exe("DELETE FROM bots WHERE bot_id=?", (bid,))

    def bot_count(self, uid):
        return (self.exe("SELECT COUNT(*) as c FROM bots WHERE user_id=?", (uid,), one=True) or {}).get('c', 0)

    # ── Payments ──
    def add_pay(self, uid, amt, method, trx, plan, days=30):
        return self.exe(
            "INSERT INTO payments(user_id,amount,method,transaction_id,plan,duration_days) VALUES(?,?,?,?,?,?)",
            (uid, amt, method, trx, plan, days))

    def pending_pay(self):
        return self.exe("SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC", fetch=True) or []

    def get_pay(self, pid):
        return self.exe("SELECT * FROM payments WHERE payment_id=?", (pid,), one=True)

    def approve_pay(self, pid, aid):
        p = self.get_pay(pid)
        if not p:
            return None
        self.exe("UPDATE payments SET status='approved',approved_by=?,processed_at=datetime('now') WHERE payment_id=?",
                 (aid, pid))
        self.set_sub(p['user_id'], p['plan'], p['duration_days'])
        return p

    def reject_pay(self, pid, aid):
        self.exe("UPDATE payments SET status='rejected',approved_by=?,processed_at=datetime('now') WHERE payment_id=?",
                 (aid, pid))

    # ── Referrals ──
    def add_ref(self, rr, rd, days=3, comm=20):
        self.exe("INSERT INTO referrals(referrer_id,referred_id,bonus_days,commission) VALUES(?,?,?,?)",
                 (rr, rd, days, comm))
        u = self.get_user(rr)
        if u:
            nc = u['referral_count'] + 1
            lv = 'diamond' if nc >= 100 else 'platinum' if nc >= 50 else 'gold' if nc >= 25 else 'silver' if nc >= 10 else 'bronze'
            self.update_user(rr, referral_count=nc, referral_earnings=u['referral_earnings'] + comm,
                             wallet_balance=u['wallet_balance'] + comm, referral_level=lv)

    def ref_board(self, lim=10):
        return self.exe("SELECT * FROM users ORDER BY referral_count DESC LIMIT ?", (lim,), fetch=True) or []

    def user_refs(self, uid):
        return self.exe("SELECT * FROM referrals WHERE referrer_id=?", (uid,), fetch=True) or []

    # ── Wallet ──
    def wallet_tx(self, uid, amt, tt, desc=''):
        self.exe("INSERT INTO wallet_tx(user_id,amount,tx_type,description) VALUES(?,?,?,?)",
                 (uid, amt, tt, desc))
        if tt in ('credit', 'referral', 'refund', 'bonus'):
            self.exe("UPDATE users SET wallet_balance=wallet_balance+? WHERE user_id=?", (amt, uid))
        elif tt in ('debit', 'withdraw', 'purchase'):
            self.exe("UPDATE users SET wallet_balance=wallet_balance-? WHERE user_id=?", (amt, uid))

    def wallet_hist(self, uid, lim=20):
        return self.exe("SELECT * FROM wallet_tx WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                         (uid, lim), fetch=True) or []

    # ── Force Channels ──
    def add_channel(self, username, name='', added_by=None):
        username = username.strip().lstrip('@').lower()
        ex = self.exe("SELECT * FROM force_channels WHERE channel_username=?", (username,), one=True)
        if ex:
            self.exe("UPDATE force_channels SET is_active=1,channel_name=? WHERE channel_username=?",
                     (name or username, username))
            return ex['channel_id']
        return self.exe("INSERT INTO force_channels(channel_username,channel_name,added_by) VALUES(?,?,?)",
                        (username, name or username, added_by))

    def remove_channel(self, username):
        self.exe("UPDATE force_channels SET is_active=0 WHERE channel_username=?",
                 (username.strip().lstrip('@').lower(),))

    def get_active_channels(self):
        return self.exe("SELECT * FROM force_channels WHERE is_active=1", fetch=True) or []

    def get_all_channels(self):
        return self.exe("SELECT * FROM force_channels ORDER BY is_active DESC", fetch=True) or []

    def toggle_channel(self, cid):
        ch = self.exe("SELECT * FROM force_channels WHERE channel_id=?", (cid,), one=True)
        if ch:
            ns = 0 if ch['is_active'] else 1
            self.exe("UPDATE force_channels SET is_active=? WHERE channel_id=?", (ns, cid))
            return ns
        return None

    def delete_channel(self, cid):
        self.exe("DELETE FROM force_channels WHERE channel_id=?", (cid,))

    # ── Tickets ──
    def add_ticket(self, uid, subj, msg):
        return self.exe("INSERT INTO tickets(user_id,subject,message) VALUES(?,?,?)", (uid, subj, msg))

    def open_tickets(self):
        return self.exe("SELECT * FROM tickets WHERE status='open' ORDER BY created_at DESC", fetch=True) or []

    def reply_ticket(self, tid, reply):
        self.exe("UPDATE tickets SET admin_reply=?,status='replied' WHERE ticket_id=?", (reply, tid))

    # ── Notifications ──
    def add_notif(self, uid, title, message):
        return self.exe("INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)", (uid, title, message))

    def get_notifs(self, uid, lim=10):
        return self.exe("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                         (uid, lim), fetch=True) or []

    def unread_count(self, uid):
        r = self.exe("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (uid,), one=True)
        return r['c'] if r else 0

    def mark_read(self, uid):
        self.exe("UPDATE notifications SET is_read=1 WHERE user_id=?", (uid,))

    # ── Admin ──
    def admin_log(self, aid, act, tgt=None, det=''):
        self.exe("INSERT INTO admin_logs(admin_id,action,target_user,details) VALUES(?,?,?,?)",
                 (aid, act, tgt, det))

    # ── Stats ──
    def stats(self):
        tu = (self.exe("SELECT COUNT(*) as c FROM users", one=True) or {}).get('c', 0)
        tb = (self.exe("SELECT COUNT(*) as c FROM bots", one=True) or {}).get('c', 0)
        pp = (self.exe("SELECT COUNT(*) as c FROM payments WHERE status='pending'", one=True) or {}).get('c', 0)
        rv = (self.exe("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='approved'", one=True) or {}).get('s', 0)
        td = (self.exe("SELECT COUNT(*) as c FROM users WHERE date(created_at)=date('now')", one=True) or {}).get('c', 0)
        ac = (self.exe("SELECT COUNT(*) as c FROM users WHERE plan!='free' AND(is_lifetime=1 OR subscription_end>datetime('now'))", one=True) or {}).get('c', 0)
        return {'users': tu, 'bots': tb, 'pending': pp, 'revenue': rv, 'today': td, 'active_subs': ac}


db = DB()

# ═══════════════════════════════════════════════════
#  SCRIPT RUNNER ENGINE
# ═══════════════════════════════════════════════════
def pip_install(mod, cid):
    pkg = MODULES_MAP.get(mod.split('.')[0].lower(), mod)
    try:
        safe_send(cid, f"📦 Installing {pkg}...")
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            safe_send(cid, f"✅ Installed {pkg}")
            return True
        return False
    except:
        return False


def run_bot(bid, cid, att=1):
    if att > 3:
        safe_send(cid, "❌ <b>Failed 3 attempts!</b> Check your code.")
        return

    bd = db.get_bot(bid)
    if not bd:
        safe_send(cid, "❌ Bot not found!")
        return

    uid = bd['user_id']
    bn = bd['bot_name']
    fp = bd['file_path']
    ef = bd['entry_file']
    ft = bd['file_type']
    sk = f"{uid}_{bn}"
    wd = fp if os.path.isdir(fp) else user_folder(uid)

    # Re-detect on first attempt
    if att == 1:
        de, dt, dr = det.report(wd)
        if de:
            ef = de
            ft = dt or 'py'
            db.update_bot(bid, entry_file=ef, file_type=ft)

    fsp = os.path.join(wd, ef)

    # Find entry file
    if not os.path.exists(fsp):
        found = False
        for root, dirs, files in os.walk(wd):
            if os.path.basename(ef) in files:
                fsp = os.path.join(root, os.path.basename(ef))
                ef = os.path.relpath(fsp, wd)
                db.update_bot(bid, entry_file=ef)
                found = True
                break
        if not found:
            af = [os.path.relpath(os.path.join(r, f), wd)
                  for r, d, fs in os.walk(wd) for f in fs if f.endswith(('.py', '.js'))]
            err = f"❌ {ef} not found!\n\nAvailable:\n"
            for f in af[:10]:
                err += f"• {f}\n"
            if not af:
                err += "(No .py or .js files)"
            safe_send(cid, err)
            return

    # Install deps on first attempt
    if att == 1:
        if ft == 'py':
            det.install_req(wd, cid)
        else:
            det.install_npm(wd, cid)

    # Starting message
    type_icon = '🐍 Python' if ft == 'py' else '🟨 Node.js'
    safe_send(cid,
        f"🚀 <b>Starting Bot...</b>\n\n"
        f"📄 {ef}\n"
        f"🔤 {type_icon}\n"
        f"🔄 Attempt: {att}/3")

    try:
        lp = os.path.join(LOGS_DIR, f"{sk}.log")
        lf = open(lp, 'w', encoding='utf-8', errors='ignore')

        cmd = ['node', fsp] if ft == 'js' else [sys.executable, '-u', fsp]

        env = os.environ.copy()
        if bd.get('bot_token'):
            env['BOT_TOKEN'] = bd['bot_token']
        env['PYTHONUNBUFFERED'] = '1'

        proc = subprocess.Popen(
            cmd, cwd=wd, stdout=lf, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='ignore', env=env,
            preexec_fn=os.setsid if os.name != 'nt' else None
        )

        bot_scripts[sk] = {
            'process': proc, 'file_name': bn, 'bot_id': bid,
            'user_id': uid, 'start_time': datetime.now(),
            'log_file': lf, 'log_path': lp, 'entry_file': ef,
            'work_dir': wd, 'type': ft, 'attempt': att,
        }

        # Wait to check if bot stays running
        time.sleep(5)
        if proc.poll() is None:
            time.sleep(3)
            if proc.poll() is None:
                db.update_bot(bid, status='running', pid=proc.pid,
                              last_started=datetime.now().isoformat(),
                              entry_file=ef, file_type=ft)
                safe_send(cid,
                    f"✅ <b>BOT IS RUNNING!</b>\n\n"
                    f"📄 {ef}\n"
                    f"🆔 PID: {proc.pid}\n"
                    f"🔤 {type_icon}\n"
                    f"⏱️ {datetime.now().strftime('%H:%M:%S')}\n"
                    f"📊 🟢 Running")
                return

        # Bot crashed
        lf.close()
        err = ""
        try:
            with open(lp, 'r', encoding='utf-8', errors='ignore') as f:
                err = f.read()[-2000:]
        except:
            pass

        # Auto-install missing Python module
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", err)
        if match:
            cleanup(sk)
            if pip_install(match.group(1).split('.')[0], cid):
                time.sleep(1)
                run_bot(bid, cid, att + 1)
                return

        # Auto-install missing npm module
        match = re.search(r"Cannot find module '([^']+)'", err)
        if match and not match.group(1).startswith('.'):
            cleanup(sk)
            try:
                subprocess.run(['npm', 'install', match.group(1)],
                               cwd=wd, capture_output=True, timeout=60)
                time.sleep(1)
                run_bot(bid, cid, att + 1)
                return
            except:
                pass

        # Try alternate entry
        if att == 1:
            for alt in ['app.py', 'main.py', 'bot.py', 'run.py', 'index.js', 'app.js']:
                if os.path.exists(os.path.join(wd, alt)) and alt != ef:
                    cleanup(sk)
                    db.update_bot(bid, entry_file=alt,
                                  file_type='js' if alt.endswith('.js') else 'py')
                    run_bot(bid, cid, att + 1)
                    return

        # Show error
        err_display = err[-500:] if err.strip() else 'No output'
        safe_send(cid,
            f"❌ <b>BOT CRASHED!</b>\n\n"
            f"📄 {ef}\n"
            f"Exit: {proc.returncode} | Attempt: {att}/3\n\n"
            f"<code>{err_display}</code>")

        db.update_bot(bid, status='crashed',
                      last_crash=datetime.now().isoformat(),
                      error_log=err[-500:])
        cleanup(sk)

    except Exception as e:
        logger.error(f"Run error: {e}", exc_info=True)
        safe_send(cid, f"❌ {str(e)[:200]}")
        cleanup(sk)


# ═══════════════════════════════════════════════════
#  BACKGROUND THREADS
# ═══════════════════════════════════════════════════
def thread_monitor():
    while True:
        try:
            for sk in list(bot_scripts.keys()):
                i = bot_scripts.get(sk)
                if not i:
                    continue
                if i.get('process') and i['process'].poll() is not None:
                    bid = i.get('bot_id')
                    uid = i.get('user_id')
                    if bid:
                        db.update_bot(bid, status='crashed', last_crash=datetime.now().isoformat())
                    if uid and bid:
                        u = db.get_user(uid)
                        if u and db.is_active(uid):
                            pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
                            if pl.get('auto_restart') and i.get('attempt', 1) < 3:
                                cleanup(sk)
                                time.sleep(5)
                                threading.Thread(target=run_bot, args=(bid, uid, i.get('attempt', 1) + 1), daemon=True).start()
                                continue
                    cleanup(sk)
        except Exception as e:
            logger.error(f"Monitor: {e}")
        time.sleep(30)


def thread_backup():
    while True:
        try:
            time.sleep(86400)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"bk_{ts}.db"))
            bks = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith('bk_')], reverse=True)
            for old in bks[10:]:
                os.remove(os.path.join(BACKUP_DIR, old))
        except:
            pass


def thread_expiry():
    while True:
        try:
            time.sleep(3600)
            now = datetime.now().isoformat()
            expired = db.exe(
                "SELECT * FROM users WHERE subscription_end<=? AND is_lifetime=0 AND plan!='free'",
                (now,), fetch=True) or []
            for u in expired:
                uid = u['user_id']
                db.rem_sub(uid)
                for b in db.get_bots(uid):
                    sk = f"{uid}_{b['bot_name']}"
                    if sk in bot_scripts:
                        kill_tree(bot_scripts[sk])
                        cleanup(sk)
                    db.update_bot(b['bot_id'], status='stopped')
                safe_send(uid,
                    f"⚠️ <b>Subscription Expired!</b>\n"
                    f"Your bots have been stopped.\n"
                    f"Renew to continue.\n\n{BRAND_TAG}")
        except:
            pass


# ═══════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════
def main_kb(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.row("🤖 My Bots", "📤 Deploy Bot")
    m.row("💎 Subscription", "💰 Wallet")
    m.row("🎁 Referral", "📊 Statistics")
    m.row("🟢 Running Bots", "⚡ Speed Test")
    m.row("🔔 Notifications", "🎫 Support")
    if uid == OWNER_ID or uid in admin_ids:
        m.row("👑 Admin Panel", "📢 Broadcast")
        m.row("🔒 Lock Bot", "💳 Payments")
    m.row("⚙️ Settings", "📞 Contact")
    return m


def bot_action_kb(bid, st):
    m = types.InlineKeyboardMarkup(row_width=2)
    if st == 'running':
        m.add(
            types.InlineKeyboardButton("🛑 Stop", callback_data=f"stop:{bid}"),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart:{bid}")
        )
        m.add(
            types.InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bid}"),
            types.InlineKeyboardButton("📊 Resources", callback_data=f"res:{bid}")
        )
    else:
        m.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"start:{bid}"),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f"del:{bid}")
        )
        m.add(
            types.InlineKeyboardButton("📥 Download", callback_data=f"dl:{bid}"),
            types.InlineKeyboardButton("📋 Logs", callback_data=f"logs:{bid}")
        )
        m.add(types.InlineKeyboardButton("🔍 Re-detect Entry", callback_data=f"redetect:{bid}"))
    m.add(types.InlineKeyboardButton("🔙 Back to Bots", callback_data="mybots"))
    return m


def plan_kb():
    m = types.InlineKeyboardMarkup(row_width=1)
    for k, p in PLAN_LIMITS.items():
        if k == 'free':
            continue
        m.add(types.InlineKeyboardButton(
            f"{p['name']} — {p['price']} BDT/mo",
            callback_data=f"plan:{k}"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu"))
    return m


def pay_method_kb(pk):
    m = types.InlineKeyboardMarkup(row_width=2)
    for k, v in PAYMENT_METHODS.items():
        m.add(types.InlineKeyboardButton(
            f"{v['icon']} {v['name']}",
            callback_data=f"pay:{pk}:{k}"))
    m.add(types.InlineKeyboardButton("💰 Pay from Wallet", callback_data=f"payw:{pk}"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="sub"))
    return m


def admin_kb():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👥 Users", callback_data="a_users"),
        types.InlineKeyboardButton("📊 Stats", callback_data="a_stats")
    )
    m.add(
        types.InlineKeyboardButton("💳 Payments", callback_data="a_pay"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="a_bc")
    )
    m.add(
        types.InlineKeyboardButton("➕ Add Sub", callback_data="a_addsub"),
        types.InlineKeyboardButton("➖ Remove Sub", callback_data="a_remsub")
    )
    m.add(
        types.InlineKeyboardButton("🚫 Ban", callback_data="a_ban"),
        types.InlineKeyboardButton("✅ Unban", callback_data="a_unban")
    )
    m.add(
        types.InlineKeyboardButton("📢 Channels", callback_data="a_channels"),
        types.InlineKeyboardButton("🎟 Promo", callback_data="a_promo")
    )
    m.add(
        types.InlineKeyboardButton("🎫 Tickets", callback_data="a_tickets"),
        types.InlineKeyboardButton("🖥 System", callback_data="a_sys")
    )
    m.add(
        types.InlineKeyboardButton("🛑 Stop All", callback_data="a_stopall"),
        types.InlineKeyboardButton("💾 Backup", callback_data="a_backup")
    )
    fsub_status = "🟢" if FORCE_SUB_ENABLED else "🔴"
    m.add(types.InlineKeyboardButton(f"{fsub_status} Force Subscribe", callback_data="a_fsub_toggle"))
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu"))
    return m


def pay_approve_kb(pid):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"appv:{pid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"rejt:{pid}")
    )
    return m


def channels_kb():
    channels = db.get_all_channels()
    m = types.InlineKeyboardMarkup(row_width=1)
    if channels:
        for ch in channels:
            status = "🟢" if ch['is_active'] else "🔴"
            m.add(types.InlineKeyboardButton(
                f"{status} @{ch['channel_username']} — {ch['channel_name']}",
                callback_data=f"ch_toggle:{ch['channel_id']}"))
    else:
        m.add(types.InlineKeyboardButton("📭 No channels added", callback_data="none"))
    m.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="ch_add"))
    m.add(types.InlineKeyboardButton("🗑 Remove Channel", callback_data="ch_remove"))
    m.add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back"))
    return m


# ═══════════════════════════════════════════════════
#  /START COMMAND
# ═══════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    un = msg.from_user.username or ''
    fn = f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip()
    active_users.add(uid)

    joined, nj = check_joined(uid)
    if not joined:
        send_force_sub(msg.chat.id, nj)
        return

    ex = db.get_user(uid)
    if ex and ex['is_banned']:
        return bot.reply_to(msg, f"🚫 Banned: {ex.get('ban_reason', '')}")
    if bot_locked and uid not in admin_ids and uid != OWNER_ID:
        return bot.reply_to(msg, "🔒 Bot is in maintenance mode.")

    is_new = ex is None
    ref_by = None
    args = msg.text.split()

    if len(args) > 1:
        rc = args[1].strip()
        rr = db.exe("SELECT user_id FROM users WHERE referral_code=?", (rc,), one=True)
        if rr and rr['user_id'] != uid and is_new:
            ref_by = rr['user_id']

    code = gen_ref_code(uid)

    if is_new:
        db.create_user(uid, un, fn, code, ref_by)
        if ref_by:
            db.add_ref(ref_by, uid, REF_BONUS_DAYS, REF_COMMISSION)
            rd = db.get_user(ref_by)
            safe_send(ref_by,
                f"🎉 <b>NEW REFERRAL!</b>\n\n"
                f"👤 {fn} joined via your link!\n"
                f"💰 +{REF_COMMISSION} BDT added!\n"
                f"📅 +{REF_BONUS_DAYS} days bonus!\n"
                f"👥 Total: {rd['referral_count'] if rd else '?'}")
    else:
        db.update_user(uid, username=un, full_name=fn, last_active=datetime.now().isoformat())
        if not ex.get('referral_code') or len(ex.get('referral_code', '')) < 5:
            db.update_user(uid, referral_code=code)

    u = db.get_user(uid)
    pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free']) if u else PLAN_LIMITS['free']
    bc = db.bot_count(uid)
    mx = '♾️' if pl['max_bots'] == -1 else str(pl['max_bots'])
    st = '👑 Owner' if uid == OWNER_ID else '⭐ Admin' if uid in admin_ids else pl['name']

    notif_count = db.unread_count(uid)
    notif_text = f"\n🔔 {notif_count} unread notifications" if notif_count > 0 else ""

    w = (
        f"🌟 <b>APON HOSTING PANEL</b> {BRAND_VER}\n"
        f"<i>Premium Bot Hosting Platform</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Welcome, <b>{fn}</b>!\n\n"
        f"📤 Deploy &amp; Host your bots\n"
        f"🚀 Python &amp; Node.js support\n"
        f"🔍 Smart Entry Detection\n"
        f"💳 bKash / Nagad / Binance\n"
        f"🎁 Earn with Referrals\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{uid}</code>\n"
        f"📦 {st}\n"
        f"🤖 Bots: {bc}/{mx}\n"
        f"💰 {u['wallet_balance'] if u else 0} BDT\n"
        f"👥 {u['referral_count'] if u else 0} referrals\n"
        f"🔑 <code>{u['referral_code'] if u else code}</code>"
        f"{notif_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    safe_send(msg.chat.id, w)
    safe_send(msg.chat.id, "⬇️ Choose an option:", reply_markup=main_kb(uid))


@bot.message_handler(commands=['help'])
def cmd_help(msg):
    safe_send(msg.chat.id,
        f"📚 <b>HELP CENTER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 <b>Deploy:</b> Send ZIP / .py / .js\n"
        f"🔍 <b>Detection:</b> Auto-finds entry file\n"
        f"🤖 <b>Control:</b> Start/Stop/Restart/Logs\n"
        f"💎 <b>Plans:</b> Free → Lifetime\n"
        f"💳 <b>Pay:</b> bKash/Nagad/Binance\n"
        f"🎁 <b>Refer:</b> Earn {REF_COMMISSION} BDT per ref\n"
        f"🎫 <b>Support:</b> Create ticket\n"
        f"👑 <b>Admin:</b> /admin\n"
        f"📞 <b>Contact:</b> {YOUR_USERNAME}\n\n"
        f"{BRAND_TAG}")


@bot.message_handler(commands=['admin'])
def cmd_admin(msg):
    show_admin(msg)


@bot.message_handler(commands=['id'])
def cmd_id(msg):
    uid = msg.from_user.id
    safe_send(msg.chat.id,
        f"🆔 <b>Your Info</b>\n\n"
        f"👤 ID: <code>{uid}</code>\n"
        f"📛 Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}\n"
        f"👤 Username: @{msg.from_user.username or 'N/A'}\n\n"
        f"{BRAND_TAG}")


@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    start = time.time()
    m = bot.reply_to(msg, "🏓 Pinging...")
    latency = round((time.time() - start) * 1000, 2)
    rn = len([k for k in bot_scripts if is_running(k)])
    safe_edit(
        f"🏓 <b>Pong!</b>\n\n"
        f"⚡ Latency: {latency}ms\n"
        f"⏱️ Uptime: {get_uptime()}\n"
        f"🤖 Running: {rn} bots\n\n"
        f"{BRAND_TAG}",
        msg.chat.id, m.message_id)


# ═══════════════════════════════════════════════════
#  TEXT HANDLER
# ═══════════════════════════════════════════════════
@bot.message_handler(content_types=['text'])
def handle_text(msg):
    uid = msg.from_user.id
    txt = msg.text
    active_users.add(uid)

    if not rate_check(uid):
        return

    joined, nj = check_joined(uid)
    if not joined:
        send_force_sub(msg.chat.id, nj)
        return

    u = db.get_user(uid)
    if u and u['is_banned']:
        return
    if bot_locked and uid not in admin_ids and uid != OWNER_ID:
        return bot.reply_to(msg, "🔒 Maintenance mode")

    if uid in payment_states:
        return handle_pay_text(msg)
    if uid in user_states:
        return handle_state(msg)

    handlers = {
        "🤖 My Bots": show_bots,
        "📤 Deploy Bot": show_deploy,
        "💎 Subscription": show_sub,
        "💰 Wallet": show_wallet,
        "🎁 Referral": show_ref,
        "📊 Statistics": show_stats,
        "🟢 Running Bots": show_running,
        "⚡ Speed Test": show_speed,
        "🔔 Notifications": show_notifs,
        "🎫 Support": show_support,
        "👑 Admin Panel": show_admin,
        "📢 Broadcast": do_broadcast,
        "🔒 Lock Bot": do_lock,
        "💳 Payments": show_payments,
        "⚙️ Settings": show_settings,
    }

    if txt in handlers:
        handlers[txt](msg)
    elif txt == "📞 Contact":
        safe_send(uid, f"📞 {YOUR_USERNAME}\n📢 {UPDATE_CHANNEL}\n\n{BRAND_TAG}")
    else:
        safe_send(uid, "❓ Use the buttons below ⬇️", reply_markup=main_kb(uid))


# ═══════════════════════════════════════════════════
#  SHOW FUNCTIONS
# ═══════════════════════════════════════════════════
def show_bots(msg):
    uid = msg.from_user.id
    bots_list = db.get_bots(uid)
    pl = db.get_plan(uid)
    mx = '♾️' if pl['max_bots'] == -1 else str(pl['max_bots'])

    if not bots_list:
        safe_send(msg.chat.id,
            f"📭 <b>No bots yet!</b>\nDeploy with 📤\n📦 Slots: 0/{mx}\n\n{BRAND_TAG}")
        return

    rn = sum(1 for b in bots_list if bot_running(uid, b['bot_name']))
    t = f"🤖 <b>My Bots</b> ({len(bots_list)}) | 🟢 {rn} | 🔴 {len(bots_list) - rn}\n📦 Limit: {mx}\n\n"
    m = types.InlineKeyboardMarkup(row_width=1)
    for b in bots_list:
        r = bot_running(uid, b['bot_name'])
        ic = "🐍" if b['file_type'] == 'py' else "🟨"
        st_icon = "🟢" if r else "🔴"
        t += f"{st_icon} {ic} {b['bot_name'][:20]} #{b['bot_id']} — {b['entry_file']}\n"
        m.add(types.InlineKeyboardButton(
            f"{st_icon} {b['bot_name'][:15]} #{b['bot_id']}",
            callback_data=f"detail:{b['bot_id']}"))
    m.add(types.InlineKeyboardButton("📤 Deploy New", callback_data="deploy"))
    safe_send(msg.chat.id, t, reply_markup=m)


def show_deploy(msg):
    uid = msg.from_user.id
    u = db.get_user(uid)
    if not u:
        return bot.reply_to(msg, "/start first!")
    pl = db.get_plan(uid)
    cur = db.bot_count(uid)
    mx = pl['max_bots']
    if mx != -1 and cur >= mx:
        return bot.reply_to(msg, f"⚠️ Limit ({cur}/{mx})! Upgrade plan.")
    rem = '♾️' if mx == -1 else str(mx - cur)
    safe_send(msg.chat.id,
        f"📤 <b>DEPLOY YOUR BOT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Send your file now!\n\n"
        f"🐍 Python (.py)\n"
        f"🟨 Node.js (.js)\n"
        f"📦 ZIP (auto-detects entry!)\n\n"
        f"🔍 <b>Smart Detection:</b>\n"
        f"app.py / main.py / bot.py\n"
        f"package.json / Procfile\n"
        f"requirements.txt (auto-install)\n\n"
        f"📦 Slots remaining: {rem}\n"
        f"━━━━━━━━━━━━━━━━━━━━")


def show_sub(msg):
    u = db.get_user(msg.from_user.id)
    if not u:
        return
    pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("📋 View Plans", callback_data="plans"))
    safe_send(msg.from_user.id,
        f"💎 <b>YOUR SUBSCRIPTION</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Plan: {pl['name']}\n"
        f"📅 Expires: {time_left(u['subscription_end'])}\n"
        f"🤖 Slots: {'♾️' if pl['max_bots'] == -1 else pl['max_bots']}\n"
        f"💾 RAM: {pl['ram']}MB\n"
        f"🔄 Auto Restart: {'✅' if pl['auto_restart'] else '❌'}\n"
        f"💰 Total Spent: {u['total_spent']} BDT\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=m)


def show_wallet(msg):
    u = db.get_user(msg.from_user.id)
    if not u:
        return
    h = db.wallet_hist(msg.from_user.id, 5)
    t = (
        f"💰 <b>WALLET</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Balance: <b>{u['wallet_balance']} BDT</b>\n"
        f"💰 Total Earned: {u['referral_earnings']} BDT\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Recent Transactions:</b>\n"
    )
    for x in h:
        ic = "➕" if x['tx_type'] in ('credit', 'referral', 'bonus') else "➖"
        t += f"{ic} {x['amount']} BDT — {x['description'][:25]}\n"
    if not h:
        t += "(No transactions yet)\n"
    safe_send(msg.from_user.id, t)


def show_ref(msg):
    uid = msg.from_user.id
    u = db.get_user(uid)
    if not u:
        return bot.reply_to(msg, "/start first!")
    rc = u.get('referral_code')
    if not rc or len(rc) < 5:
        rc = gen_ref_code(uid)
        db.update_user(uid, referral_code=rc)
        u = db.get_user(uid)
        rc = u['referral_code']

    lnk = f"https://t.me/{BOT_USERNAME}?start={rc}"
    lvl_icons = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💠', 'diamond': '💎'}

    t = (
        f"🎁 <b>REFERRAL PROGRAM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 Code: <code>{rc}</code>\n"
        f"🔗 Link:\n<code>{lnk}</code>\n\n"
        f"👥 Referrals: {u['referral_count']}\n"
        f"{lvl_icons.get(u['referral_level'], '🥉')} Level: {u['referral_level'].title()}\n"
        f"💰 Earned: {u['referral_earnings']} BDT\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 {REF_COMMISSION} BDT + 📅 {REF_BONUS_DAYS} days per ref\n"
        f"👆 Tap link to copy!"
    )

    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        types.InlineKeyboardButton("📋 Copy Link", callback_data=f"cpref:{rc}"),
        types.InlineKeyboardButton("🏆 Leaderboard", callback_data="board"),
        types.InlineKeyboardButton("📋 My Referrals", callback_data="myrefs"),
        types.InlineKeyboardButton("📤 Share", switch_inline_query=f"🚀 Join {BRAND}!\n{lnk}")
    )
    safe_send(uid, t, reply_markup=m)


def show_stats(msg):
    s = db.stats()
    ss = sys_stats()
    rn = len([k for k in bot_scripts if is_running(k)])
    safe_send(msg.chat.id,
        f"📊 <b>SYSTEM STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥️ CPU: {ss['cpu']}%\n"
        f"🧠 RAM: {ss['mem']}%\n"
        f"💾 Disk: {ss['disk']}%\n"
        f"⏱️ Uptime: {ss['up']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Running: {rn}\n"
        f"👥 Total Users: {s['users']}\n"
        f"📅 Today: {s['today']}\n"
        f"💎 Active Subs: {s['active_subs']}\n"
        f"💰 Revenue: {s['revenue']} BDT\n"
        f"━━━━━━━━━━━━━━━━━━━━")


def show_running(msg):
    uid = msg.from_user.id
    r = []
    for sk, i in bot_scripts.items():
        if is_running(sk) and (uid == OWNER_ID or uid in admin_ids or i.get('user_id') == uid):
            up = str(datetime.now() - i.get('start_time', datetime.now())).split('.')[0]
            ram, cpu = bot_res(sk)
            r.append(f"📄 {i.get('file_name', '?')[:20]}\n   PID:{i['process'].pid} ⏱️{up} 💾{ram}MB")
    t = f"🟢 <b>Running ({len(r)})</b>\n\n" + "\n".join(r) if r else "🔴 No bots running."
    safe_send(msg.chat.id, t)


def show_speed(msg):
    ss = sys_stats()
    safe_send(msg.chat.id,
        f"⚡ <b>Speed Test</b>\n\n"
        f"🖥️ CPU: {ss['cpu']}%\n"
        f"🧠 RAM: {ss['mem']}%\n"
        f"💾 Disk: {ss['disk']}%\n"
        f"🌐 Mem: {ss['mem_total']}\n"
        f"⏱️ {ss['up']}")


def show_notifs(msg):
    uid = msg.from_user.id
    notifs = db.get_notifs(uid, 10)
    t = f"🔔 <b>Notifications</b>\n\n"
    for n in notifs:
        ic = "🔴" if not n['is_read'] else "⚪"
        t += f"{ic} <b>{n['title']}</b>\n{n['message'][:50]}\n\n"
    if not notifs:
        t += "No notifications yet!"
    db.mark_read(uid)
    safe_send(uid, t)


def show_support(msg):
    uid = msg.from_user.id
    user_states[uid] = {'action': 'ticket'}
    safe_send(uid,
        f"🎫 <b>Create Support Ticket</b>\n\n"
        f"Send your issue/question in one message.\n"
        f"Our team will respond ASAP!\n\n"
        f"📞 Direct: {YOUR_USERNAME}\n\n"
        f"{BRAND_TAG}")


def show_settings(msg):
    uid = msg.from_user.id
    u = db.get_user(uid)
    if not u:
        return
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang:en"),
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang:bn")
    )
    m.add(types.InlineKeyboardButton("📊 My Profile", callback_data="profile"))
    m.add(types.InlineKeyboardButton("💳 Payment History", callback_data="pay_history"))
    safe_send(uid,
        f"⚙️ <b>Settings</b>\n"
        f"👤 {u['full_name']}\n"
        f"🆔 <code>{uid}</code>\n"
        f"📅 Joined: {u['created_at'][:10] if u.get('created_at') else '?'}\n"
        f"📦 Plan: {PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])['name']}\n\n"
        f"{BRAND_TAG}",
        reply_markup=m)


def show_admin(msg):
    uid = msg.from_user.id
    if uid != OWNER_ID and uid not in admin_ids:
        return bot.reply_to(msg, "❌ Admin only!")
    s = db.stats()
    rn = len([k for k in bot_scripts if is_running(k)])
    tickets = len(db.open_tickets())
    safe_send(uid,
        f"👑 <b>ADMIN PANEL</b>\n"
        f"{BRAND_TAG}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: {s['users']} (+{s['today']} today)\n"
        f"🤖 Running: {rn}\n"
        f"💎 Active Subs: {s['active_subs']}\n"
        f"💳 Pending: {s['pending']}\n"
        f"🎫 Open Tickets: {tickets}\n"
        f"💰 Revenue: {s['revenue']} BDT\n"
        f"Force Sub: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=admin_kb())


def do_broadcast(msg):
    if msg.from_user.id not in admin_ids and msg.from_user.id != OWNER_ID:
        return
    user_states[msg.from_user.id] = {'action': 'broadcast'}
    bot.reply_to(msg, "📢 Send broadcast message:")


def do_lock(msg):
    global bot_locked
    if msg.from_user.id not in admin_ids and msg.from_user.id != OWNER_ID:
        return
    bot_locked = not bot_locked
    bot.reply_to(msg, f"{'🔒 LOCKED' if bot_locked else '🔓 UNLOCKED'}")


def show_payments(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    pays = db.pending_pay()
    if not pays:
        return safe_send(uid, "💳 No pending payments!")
    t = f"💳 <b>Pending ({len(pays)})</b>\n\n"
    m = types.InlineKeyboardMarkup(row_width=2)
    for p in pays[:10]:
        u = db.get_user(p['user_id'])
        name = u['full_name'] if u else str(p['user_id'])
        t += f"#{p['payment_id']} — {name}\n💰 {p['amount']} {p['method']} TRX:{p['transaction_id'][:15]}\n\n"
        m.add(
            types.InlineKeyboardButton(f"✅ #{p['payment_id']}", callback_data=f"appv:{p['payment_id']}"),
            types.InlineKeyboardButton(f"❌ #{p['payment_id']}", callback_data=f"rejt:{p['payment_id']}")
        )
    safe_send(uid, t, reply_markup=m)


# ═══════════════════════════════════════════════════
#  DOCUMENT HANDLER
# ═══════════════════════════════════════════════════
@bot.message_handler(content_types=['document'])
def handle_doc(msg):
    uid = msg.from_user.id

    joined, nj = check_joined(uid)
    if not joined:
        send_force_sub(msg.chat.id, nj)
        return

    u = db.get_user(uid)
    if not u:
        return bot.reply_to(msg, "Please /start first!")
    if u['is_banned']:
        return

    pl = db.get_plan(uid)
    cur = db.bot_count(uid)
    mx = pl['max_bots']
    if mx != -1 and cur >= mx:
        return bot.reply_to(msg, f"❌ Bot limit reached ({cur}/{mx})! Upgrade your plan.")

    fn = msg.document.file_name
    fs = msg.document.file_size
    ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''

    allowed = ['py', 'js', 'zip', 'json', 'txt', 'env', 'yml', 'yaml', 'cfg', 'ini', 'toml']
    if ext not in allowed:
        return bot.reply_to(msg, f"❌ Unsupported file type: .{ext}")

    if fs > 100 * 1024 * 1024:
        return bot.reply_to(msg, "❌ File too large! Max 100MB.")

    pm = bot.reply_to(msg, f"📤 Uploading {fn[:25]} ({fmt_size(fs)})...")

    try:
        fi = bot.get_file(msg.document.file_id)
        dl = bot.download_file(fi.file_path)

        uf = user_folder(uid)

        # ── ZIP UPLOAD ──
        if ext == 'zip':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                tmp.write(dl)
                tp = tmp.name

            try:
                with zipfile.ZipFile(tp, 'r') as z:
                    for n in z.namelist():
                        if n.startswith('/') or '..' in n:
                            safe_edit("❌ Suspicious file paths!", msg.chat.id, pm.message_id)
                            os.unlink(tp)
                            return

                    bn = fn.replace('.zip', '').replace(' ', '_')
                    ed = os.path.join(uf, bn)

                    if os.path.exists(ed):
                        shutil.rmtree(ed, ignore_errors=True)
                    os.makedirs(ed, exist_ok=True)

                    z.extractall(ed)

                    # Handle single root folder
                    items = os.listdir(ed)
                    if len(items) == 1 and os.path.isdir(os.path.join(ed, items[0])):
                        inner = os.path.join(ed, items[0])
                        for item in os.listdir(inner):
                            src = os.path.join(inner, item)
                            dst = os.path.join(ed, item)
                            if os.path.exists(dst):
                                if os.path.isdir(dst):
                                    shutil.rmtree(dst)
                                else:
                                    os.remove(dst)
                            shutil.move(src, dst)
                        try:
                            os.rmdir(inner)
                        except:
                            pass

                os.unlink(tp)

                entry, ft, report = det.report(ed)

                if not entry:
                    af = []
                    for r, d, fs_list in os.walk(ed):
                        for f in fs_list:
                            if f.endswith(('.py', '.js')):
                                af.append(os.path.relpath(os.path.join(r, f), ed))

                    err_text = f"❌ <b>No entry file detected!</b>\n\nFiles in ZIP:\n"
                    for f in af[:15]:
                        err_text += f"• {f}\n"
                    if not af:
                        err_text += "(No .py or .js files)\n"
                    err_text += "\nMake sure ZIP has app.py, main.py, or bot.py"
                    safe_edit(err_text, msg.chat.id, pm.message_id)
                    return

                bid = db.add_bot(uid, bn, ed, entry, ft, '', fs, '')

                mk = types.InlineKeyboardMarkup(row_width=2)
                mk.add(
                    types.InlineKeyboardButton("▶️ Start Now", callback_data=f"start:{bid}"),
                    types.InlineKeyboardButton("🤖 My Bots", callback_data="mybots")
                )
                mk.add(types.InlineKeyboardButton("🔍 Re-detect", callback_data=f"redetect:{bid}"))

                safe_edit(
                    f"✅ <b>ZIP DEPLOYED!</b>\n\n"
                    f"📦 {bn[:20]}\n"
                    f"🆔 Bot ID: #{bid}\n\n"
                    f"🔍 Detection:\n{report}",
                    msg.chat.id, pm.message_id, reply_markup=mk)

            except zipfile.BadZipFile:
                safe_edit("❌ Invalid or corrupted ZIP file!", msg.chat.id, pm.message_id)
                try:
                    os.unlink(tp)
                except:
                    pass

        # ── SINGLE FILE (.py / .js) ──
        elif ext in ['py', 'js']:
            file_path = os.path.join(uf, fn)
            with open(file_path, 'wb') as f:
                f.write(dl)

            bid = db.add_bot(uid, fn, uf, fn, ext, '', fs, 'exact')

            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(
                types.InlineKeyboardButton("▶️ Run Now", callback_data=f"start:{bid}"),
                types.InlineKeyboardButton("🤖 My Bots", callback_data="mybots")
            )

            safe_edit(
                f"✅ <b>FILE UPLOADED!</b>\n\n"
                f"📄 {fn[:25]}\n"
                f"🆔 Bot ID: #{bid}\n"
                f"🔤 {'🐍 Python' if ext == 'py' else '🟨 Node.js'}\n"
                f"📊 {fmt_size(fs)}",
                msg.chat.id, pm.message_id, reply_markup=mk)

        # ── CONFIG FILES ──
        else:
            file_path = os.path.join(uf, fn)
            with open(file_path, 'wb') as f:
                f.write(dl)
            safe_edit(f"✅ Config file {fn} saved!", msg.chat.id, pm.message_id)

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        safe_edit(f"❌ Error: {str(e)[:100]}", msg.chat.id, pm.message_id)


# ═══════════════════════════════════════════════════
#  STATE HANDLERS
# ═══════════════════════════════════════════════════
def handle_state(msg):
    uid = msg.from_user.id
    s = user_states.get(uid)
    if not s:
        return

    action = s.get('action')

    if action == 'broadcast':
        if uid not in admin_ids and uid != OWNER_ID:
            user_states.pop(uid, None)
            return
        text = msg.text
        users = db.get_all_users()
        sent = failed = 0
        prog = bot.reply_to(msg, f"📢 Broadcasting to {len(users)} users...")
        for u in users:
            try:
                safe_send(u['user_id'], f"📢 <b>Broadcast</b>\n\n{text}\n\n{BRAND_TAG}")
                sent += 1
            except:
                failed += 1
            if (sent + failed) % 50 == 0:
                safe_edit(f"📢 Progress: {sent + failed}/{len(users)}\n✅ {sent} | ❌ {failed}",
                          msg.chat.id, prog.message_id)
        safe_edit(f"📢 <b>Broadcast Complete!</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {len(users)}",
                  msg.chat.id, prog.message_id)
        db.admin_log(uid, 'broadcast', details=f"sent:{sent} failed:{failed}")
        user_states.pop(uid, None)

    elif action == 'a_addsub' and s.get('step', 1) == 1:
        try:
            target = int(msg.text.strip())
            target_user = db.get_user(target)
            if not target_user:
                bot.reply_to(msg, f"❌ User {target} not found!")
                user_states.pop(uid, None)
                return
            user_states[uid] = {'action': 'a_addsub', 'step': 2, 'target': target}
            m = types.InlineKeyboardMarkup(row_width=2)
            for k, p in PLAN_LIMITS.items():
                if k != 'free':
                    m.add(types.InlineKeyboardButton(p['name'], callback_data=f"asub:{k}:{target}"))
            bot.reply_to(msg,
                f"👤 User: <code>{target}</code> — {target_user['full_name']}\n"
                f"Current: {PLAN_LIMITS.get(target_user['plan'], PLAN_LIMITS['free'])['name']}\n\n"
                f"Select new plan:", parse_mode='HTML', reply_markup=m)
            return
        except ValueError:
            bot.reply_to(msg, "❌ Invalid user ID!")
            user_states.pop(uid, None)

    elif action == 'a_addsub_days':
        try:
            days = int(msg.text.strip())
            target = s['target']
            plan = s['plan']
            if days == 0:
                db.set_sub(target, 'lifetime')
                plan_name = "👑 Lifetime"
            else:
                db.set_sub(target, plan, days)
                plan_name = PLAN_LIMITS.get(plan, {}).get('name', plan)
            bot.reply_to(msg,
                f"✅ <b>Subscription Added!</b>\n\n"
                f"👤 User: <code>{target}</code>\n"
                f"📦 Plan: {plan_name}\n"
                f"📅 Duration: {'Lifetime' if days == 0 else f'{days} days'}",
                parse_mode='HTML')
            db.admin_log(uid, 'add_sub', target, f"{plan}/{days}d")
            safe_send(target,
                f"🎉 <b>Plan Upgraded!</b>\n\n"
                f"📦 New Plan: {plan_name}\n"
                f"📅 Duration: {'Lifetime' if days == 0 else f'{days} days'}\n\n{BRAND_TAG}")
        except ValueError:
            bot.reply_to(msg, "❌ Invalid! Send a number (0 = lifetime).")
        user_states.pop(uid, None)

    elif action == 'a_remsub':
        try:
            target = int(msg.text.strip())
            db.rem_sub(target)
            bot.reply_to(msg, f"✅ Subscription removed: <code>{target}</code>", parse_mode='HTML')
            db.admin_log(uid, 'remove_sub', target)
            safe_send(target, "⚠️ Your subscription has been removed by admin.")
        except:
            bot.reply_to(msg, "❌ Invalid user ID!")
        user_states.pop(uid, None)

    elif action == 'a_ban':
        parts = msg.text.strip().split(maxsplit=1)
        try:
            target = int(parts[0])
            reason = parts[1] if len(parts) > 1 else "Banned by admin"
            db.ban(target, reason)
            db.admin_log(uid, 'ban', target, reason)
            for b in db.get_bots(target):
                sk = f"{target}_{b['bot_name']}"
                if sk in bot_scripts:
                    kill_tree(bot_scripts[sk])
                    cleanup(sk)
                db.update_bot(b['bot_id'], status='stopped')
            bot.reply_to(msg, f"🚫 Banned <code>{target}</code>\nReason: {reason}", parse_mode='HTML')
            safe_send(target, f"🚫 <b>You have been banned!</b>\nReason: {reason}\n\nContact {YOUR_USERNAME}")
        except:
            bot.reply_to(msg, "❌ Format: USER_ID REASON")
        user_states.pop(uid, None)

    elif action == 'a_unban':
        try:
            target = int(msg.text.strip())
            db.unban(target)
            db.admin_log(uid, 'unban', target)
            bot.reply_to(msg, f"✅ Unbanned <code>{target}</code>", parse_mode='HTML')
            safe_send(target, "✅ You have been unbanned! Welcome back.")
        except:
            bot.reply_to(msg, "❌ Invalid user ID!")
        user_states.pop(uid, None)

    elif action == 'a_promo':
        parts = msg.text.strip().split()
        if len(parts) >= 3:
            try:
                code = parts[0].upper()
                discount = int(parts[1])
                max_uses = int(parts[2])
                db.exe("INSERT OR IGNORE INTO promo_codes(code,discount_pct,max_uses,created_by) VALUES(?,?,?,?)",
                       (code, discount, max_uses, uid))
                bot.reply_to(msg,
                    f"✅ <b>Promo Created!</b>\n\n"
                    f"🎟 Code: <code>{code}</code>\n"
                    f"💰 Discount: {discount}%\n"
                    f"🔢 Max Uses: {max_uses}", parse_mode='HTML')
                db.admin_log(uid, 'create_promo', details=f"{code}/{discount}%/{max_uses}")
            except:
                bot.reply_to(msg, "❌ Error!")
        else:
            bot.reply_to(msg, "❌ Format: CODE DISCOUNT% MAX_USES\nEx: SAVE50 50 100")
        user_states.pop(uid, None)

    elif action == 'ch_add':
        text = msg.text.strip()
        if not text:
            bot.reply_to(msg, "❌ Send channel username!")
            user_states.pop(uid, None)
            return
        parts = text.split(maxsplit=1)
        ch_username = parts[0].lstrip('@').lower()
        ch_name = parts[1] if len(parts) > 1 else ch_username
        try:
            chat_info = bot.get_chat(f"@{ch_username}")
            ch_name = chat_info.title or ch_name
        except:
            pass
        cid_ch = db.add_channel(ch_username, ch_name, uid)
        db.admin_log(uid, 'add_channel', details=f"@{ch_username}")
        bot.reply_to(msg,
            f"✅ <b>Channel Added!</b>\n\n"
            f"📢 @{ch_username}\n📝 {ch_name}\n\n"
            f"⚠️ Make sure bot is admin!", parse_mode='HTML')
        user_states.pop(uid, None)

    elif action == 'ch_remove':
        text = msg.text.strip().lstrip('@').lower()
        if not text:
            bot.reply_to(msg, "❌ Send channel username!")
            user_states.pop(uid, None)
            return
        db.remove_channel(text)
        db.admin_log(uid, 'remove_channel', details=f"@{text}")
        bot.reply_to(msg, f"✅ Removed @{text} from force subscribe!")
        user_states.pop(uid, None)

    elif action == 'ticket':
        text = msg.text.strip()
        if len(text) < 5:
            bot.reply_to(msg, "❌ Message too short!")
            user_states.pop(uid, None)
            return
        tid = db.add_ticket(uid, "Support Request", text)
        bot.reply_to(msg,
            f"✅ <b>Ticket #{tid} Created!</b>\n\n"
            f"📝 {text[:100]}...\n\n"
            f"Our team will respond soon.\n{YOUR_USERNAME}\n\n{BRAND_TAG}",
            parse_mode='HTML')
        u = db.get_user(uid)
        for aid in admin_ids:
            safe_send(aid,
                f"🎫 <b>New Ticket #{tid}</b>\n\n"
                f"👤 {u['full_name'] if u else uid} (<code>{uid}</code>)\n"
                f"📝 {text[:200]}\n\n"
                f"Reply: /reply {tid} your_message")
        user_states.pop(uid, None)

    elif action == 'ticket_reply':
        tid = s.get('ticket_id')
        text = msg.text.strip()
        if not text or not tid:
            user_states.pop(uid, None)
            return
        ticket = db.exe("SELECT * FROM tickets WHERE ticket_id=?", (tid,), one=True)
        if ticket:
            db.reply_ticket(tid, text)
            bot.reply_to(msg, f"✅ Replied to ticket #{tid}")
            safe_send(ticket['user_id'],
                f"📩 <b>Ticket #{tid} Reply</b>\n\n💬 {text}\n\nFrom: Admin\n{BRAND_TAG}")
        user_states.pop(uid, None)

    else:
        user_states.pop(uid, None)


# ═══════════════════════════════════════════════════
#  PAYMENT TEXT HANDLER
# ═══════════════════════════════════════════════════
def handle_pay_text(msg):
    uid = msg.from_user.id
    s = payment_states.get(uid)
    if not s or s.get('step') != 'wait_trx':
        return

    trx = msg.text.strip() if msg.text else 'SCREENSHOT'
    if not trx or len(trx) < 3:
        return bot.reply_to(msg, "❌ Please send a valid Transaction ID!")

    pid = db.add_pay(uid, s['amount'], s['method'], trx, s['plan'], 30)
    payment_states.pop(uid, None)

    safe_send(uid,
        f"✅ <b>PAYMENT SUBMITTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Payment ID: #{pid}\n"
        f"💰 Amount: {s['amount']} BDT\n"
        f"💳 Method: {s['method']}\n"
        f"📦 Plan: {s['plan']}\n"
        f"🔖 TRX: <code>{trx}</code>\n\n"
        f"⏳ Waiting for admin approval...\n"
        f"━━━━━━━━━━━━━━━━━━━━")

    u = db.get_user(uid)
    for aid in admin_ids:
        method_info = PAYMENT_METHODS.get(s['method'], {})
        safe_send(aid,
            f"💳 <b>NEW PAYMENT!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 {u['full_name'] if u else '?'} (<code>{uid}</code>)\n"
            f"📦 Plan: {s['plan']}\n"
            f"💰 Amount: {s['amount']} BDT\n"
            f"{method_info.get('icon', '💳')} Method: {method_info.get('name', s['method'])}\n"
            f"🔖 TRX: <code>{trx}</code>\n"
            f"🆔 Payment #{pid}\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            reply_markup=pay_approve_kb(pid))


# ═══════════════════════════════════════════════════
#  ADMIN COMMANDS
# ═══════════════════════════════════════════════════
@bot.message_handler(commands=['reply'])
def cmd_reply_ticket(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(msg, "Usage: /reply TICKET_ID MESSAGE")
    try:
        tid = int(parts[1])
        reply_text = parts[2]
        ticket = db.exe("SELECT * FROM tickets WHERE ticket_id=?", (tid,), one=True)
        if not ticket:
            return bot.reply_to(msg, f"❌ Ticket #{tid} not found!")
        db.reply_ticket(tid, reply_text)
        bot.reply_to(msg, f"✅ Replied to ticket #{tid}")
        safe_send(ticket['user_id'], f"📩 <b>Ticket #{tid} — Admin Reply</b>\n\n💬 {reply_text}\n\n{BRAND_TAG}")
    except ValueError:
        bot.reply_to(msg, "❌ Invalid ticket ID!")


@bot.message_handler(commands=['subscribe'])
def cmd_sub_admin(msg):
    if msg.from_user.id not in admin_ids and msg.from_user.id != OWNER_ID:
        return
    p = msg.text.split()
    if len(p) < 3:
        return bot.reply_to(msg, "/subscribe UID DAYS")
    try:
        db.set_sub(int(p[1]), 'pro' if int(p[2]) > 0 else 'lifetime', int(p[2]))
        bot.reply_to(msg, "✅ Done")
    except:
        bot.reply_to(msg, "❌ Error")


@bot.message_handler(commands=['ban'])
def cmd_ban(msg):
    if msg.from_user.id not in admin_ids and msg.from_user.id != OWNER_ID:
        return
    p = msg.text.split(maxsplit=2)
    if len(p) < 2:
        return
    try:
        db.ban(int(p[1]), p[2] if len(p) > 2 else "Banned")
        bot.reply_to(msg, "🚫 Banned")
    except:
        pass


@bot.message_handler(commands=['unban'])
def cmd_unban(msg):
    if msg.from_user.id not in admin_ids and msg.from_user.id != OWNER_ID:
        return
    try:
        db.unban(int(msg.text.split()[1]))
        bot.reply_to(msg, "✅ Unbanned")
    except:
        pass


@bot.message_handler(commands=['addchannel'])
def cmd_add_channel(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /addchannel @username Channel Name")
    ch_username = parts[1].lstrip('@').lower()
    ch_name = parts[2] if len(parts) > 2 else ch_username
    try:
        chat_info = bot.get_chat(f"@{ch_username}")
        ch_name = chat_info.title or ch_name
    except:
        pass
    db.add_channel(ch_username, ch_name, uid)
    db.admin_log(uid, 'add_channel', details=f"@{ch_username}")
    bot.reply_to(msg, f"✅ Channel @{ch_username} added!\n⚠️ Make sure bot is admin!", parse_mode='HTML')


@bot.message_handler(commands=['removechannel', 'rmchannel'])
def cmd_remove_channel(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /removechannel @username")
    db.remove_channel(parts[1].lstrip('@').lower())
    bot.reply_to(msg, f"✅ Removed!")


@bot.message_handler(commands=['channels'])
def cmd_channels(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    channels = db.get_all_channels()
    t = f"📢 <b>Force Subscribe Channels</b>\nStatus: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}\n\n"
    if channels:
        for ch in channels:
            st = "🟢" if ch['is_active'] else "🔴"
            t += f"{st} @{ch['channel_username']} — {ch['channel_name']}\n"
    else:
        t += "No channels. Default: @developer_apon_07\n"
    safe_send(uid, t)


@bot.message_handler(commands=['broadcast', 'bc'])
def cmd_broadcast(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    text = msg.text.split(maxsplit=1)
    if len(text) < 2:
        user_states[uid] = {'action': 'broadcast'}
        return bot.reply_to(msg, "📢 Send broadcast message:")
    bc_text = text[1]
    users = db.get_all_users()
    sent = failed = 0
    for u in users:
        try:
            safe_send(u['user_id'], f"📢 <b>Announcement</b>\n\n{bc_text}\n\n{BRAND_TAG}")
            sent += 1
        except:
            failed += 1
    bot.reply_to(msg, f"📢 Done! ✅ {sent} | ❌ {failed}")


@bot.message_handler(commands=['userinfo'])
def cmd_userinfo(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /userinfo USER_ID")
    try:
        target = int(parts[1])
        u = db.get_user(target)
        if not u:
            return bot.reply_to(msg, f"❌ User {target} not found!")
        pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
        bc = db.bot_count(target)
        bots_list = db.get_bots(target)
        running = sum(1 for b in bots_list if bot_running(target, b['bot_name']))
        safe_send(uid,
            f"👤 <b>User Info</b>\n\n"
            f"🆔 ID: <code>{target}</code>\n"
            f"📛 Name: {u['full_name']}\n"
            f"👤 @{u['username'] or 'N/A'}\n"
            f"🚫 Banned: {'Yes — ' + u['ban_reason'] if u['is_banned'] else 'No'}\n\n"
            f"📦 Plan: {pl['name']}\n"
            f"📅 Expires: {time_left(u['subscription_end'])}\n"
            f"👑 Lifetime: {'Yes' if u['is_lifetime'] else 'No'}\n\n"
            f"🤖 Bots: {bc} (🟢 {running})\n"
            f"💰 Wallet: {u['wallet_balance']} BDT\n"
            f"💳 Spent: {u['total_spent']} BDT\n\n"
            f"👥 Refs: {u['referral_count']}\n"
            f"🔑 Code: <code>{u['referral_code']}</code>\n"
            f"📅 Joined: {u['created_at'][:16] if u.get('created_at') else '?'}")
    except ValueError:
        bot.reply_to(msg, "❌ Invalid user ID!")


@bot.message_handler(commands=['stopbot'])
def cmd_stopbot(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /stopbot BOT_ID")
    try:
        bid = int(parts[1])
        bd = db.get_bot(bid)
        if not bd:
            return bot.reply_to(msg, "❌ Bot not found!")
        sk = f"{bd['user_id']}_{bd['bot_name']}"
        if sk in bot_scripts:
            kill_tree(bot_scripts[sk])
            cleanup(sk)
        db.update_bot(bid, status='stopped')
        bot.reply_to(msg, f"✅ Stopped bot #{bid}")
    except:
        bot.reply_to(msg, "❌ Error!")


@bot.message_handler(commands=['give'])
def cmd_give(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split()
    if len(parts) < 3:
        return bot.reply_to(msg, "Usage: /give USER_ID AMOUNT")
    try:
        target = int(parts[1])
        amount = float(parts[2])
        u = db.get_user(target)
        if not u:
            return bot.reply_to(msg, f"❌ User {target} not found!")
        db.wallet_tx(target, amount, 'bonus', f"Admin bonus by {uid}")
        bot.reply_to(msg, f"✅ Gave {amount} BDT to <code>{target}</code>", parse_mode='HTML')
        safe_send(target, f"🎁 <b>Bonus!</b>\n💰 +{amount} BDT added!\n\n{BRAND_TAG}")
    except:
        bot.reply_to(msg, "❌ Error!")


@bot.message_handler(commands=['notify'])
def cmd_notify(msg):
    uid = msg.from_user.id
    if uid not in admin_ids and uid != OWNER_ID:
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(msg, "Usage: /notify USER_ID MESSAGE")
    try:
        target = int(parts[1])
        text = parts[2]
        db.add_notif(target, "Admin Notice", text)
        bot.reply_to(msg, f"✅ Sent to <code>{target}</code>", parse_mode='HTML')
        safe_send(target, f"🔔 <b>Notification</b>\n\n{text}\n\n{BRAND_TAG}")
    except:
        bot.reply_to(msg, "❌ Error!")


# ═══════════════════════════════════════════════════
#  CALLBACK HANDLER
# ═══════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global FORCE_SUB_ENABLED
    uid = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    try:
        # ── VERIFY JOIN ──
        if data == "verify_join":
            joined, nj = check_joined(uid)
            if joined:
                safe_answer(call.id, "✅ Verified! Welcome!", show_alert=True)
                try:
                    bot.delete_message(chat_id, msg_id)
                except:
                    pass
                class FakeMsg:
                    def __init__(self, c):
                        self.from_user = c.from_user
                        self.chat = c.message.chat
                        self.text = "/start"
                cmd_start(FakeMsg(call))
            else:
                safe_answer(call.id, "❌ Join all channels first!", show_alert=True)
            return

        # ── MENU ──
        elif data == "menu":
            safe_answer(call.id)
            try:
                bot.delete_message(chat_id, msg_id)
            except:
                pass
            safe_send(uid, "🏠 Main Menu", reply_markup=main_kb(uid))

        # ── MY BOTS ──
        elif data == "mybots":
            safe_answer(call.id)
            class M:
                def __init__(s, c):
                    s.chat = c.message.chat
                    s.from_user = c.from_user
            show_bots(M(call))

        # ── BOT DETAIL ──
        elif data.startswith("detail:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Bot not found!")

            sk = f"{bd['user_id']}_{bd['bot_name']}"
            rn = is_running(sk)
            ram, cpu = bot_res(sk) if rn else (0, 0)

            uptime_str = "—"
            if rn and sk in bot_scripts:
                st = bot_scripts[sk].get('start_time')
                if st:
                    uptime_str = str(datetime.now() - st).split('.')[0]

            icon = "🐍" if bd['file_type'] == 'py' else "🟨"
            status_icon = "🟢 Running" if rn else "🔴 Stopped"

            t = (
                f"{icon} <b>{bd['bot_name'][:22]}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 Bot ID: #{bid}\n"
                f"📄 Entry: {bd['entry_file']}\n"
                f"🔤 Type: {bd['file_type'].upper()}\n"
                f"📊 Status: {status_icon}\n"
                f"💾 RAM: {ram}MB | ⚡ CPU: {cpu}%\n"
                f"⏱️ Uptime: {uptime_str}\n"
                f"🔄 Restarts: {bd['total_restarts']}\n"
                f"📅 Created: {bd['created_at'][:10] if bd.get('created_at') else '?'}\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )

            kb = bot_action_kb(bid, 'running' if rn else 'stopped')
            safe_edit(t, chat_id, msg_id, reply_markup=kb)
            safe_answer(call.id)

        # ── BOT START ──
        elif data.startswith("start:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!")
            if not db.is_active(bd['user_id']):
                return safe_answer(call.id, "⚠️ Subscription expired!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if is_running(sk):
                return safe_answer(call.id, "⚠️ Already running!")
            safe_answer(call.id, "🚀 Starting...")
            threading.Thread(target=run_bot, args=(bid, chat_id), daemon=True).start()

        # ── BOT STOP ──
        elif data.startswith("stop:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!")
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if sk in bot_scripts:
                kill_tree(bot_scripts[sk])
                cleanup(sk)
            db.update_bot(bid, status='stopped', last_stopped=datetime.now().isoformat())
            safe_answer(call.id, "✅ Stopped!")
            call.data = f"detail:{bid}"
            handle_callback(call)

        # ── BOT RESTART ──
        elif data.startswith("restart:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!")
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if sk in bot_scripts:
                kill_tree(bot_scripts[sk])
                cleanup(sk)
            time.sleep(2)
            safe_answer(call.id, "🔄 Restarting...")
            threading.Thread(target=run_bot, args=(bid, chat_id), daemon=True).start()

        # ── LOGS ──
        elif data.startswith("logs:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌!")
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            lp = os.path.join(LOGS_DIR, f"{sk}.log")
            logs = "📭 No logs."
            if os.path.exists(lp):
                try:
                    with open(lp, 'r', encoding='utf-8', errors='ignore') as f:
                        logs = f.read()[-1500:] or "📭 Empty."
                except:
                    logs = "❌ Error reading logs."

            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("🔄 Refresh", callback_data=f"logs:{bid}"),
                types.InlineKeyboardButton("🗑 Clear", callback_data=f"clearlogs:{bid}")
            )
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"detail:{bid}"))
            safe_edit(f"📋 <b>Logs — #{bid}</b>\n\n<code>{logs}</code>"[:4000], chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("clearlogs:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if bd:
                sk = f"{bd['user_id']}_{bd['bot_name']}"
                lp = os.path.join(LOGS_DIR, f"{sk}.log")
                try:
                    with open(lp, 'w') as f:
                        f.write("")
                except:
                    pass
            safe_answer(call.id, "🗑 Cleared!")
            call.data = f"logs:{bid}"
            handle_callback(call)

        # ── RESOURCES ──
        elif data.startswith("res:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "!")
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            ram, cpu = bot_res(sk)
            uptime_str = "—"
            if sk in bot_scripts:
                st = bot_scripts[sk].get('start_time')
                if st:
                    uptime_str = str(datetime.now() - st).split('.')[0]
            m = types.InlineKeyboardMarkup()
            m.add(
                types.InlineKeyboardButton("🔄 Refresh", callback_data=f"res:{bid}"),
                types.InlineKeyboardButton("🔙 Back", callback_data=f"detail:{bid}")
            )
            safe_edit(f"📊 <b>Resources — #{bid}</b>\n\n💾 RAM: {ram}MB\n⚡ CPU: {cpu}%\n⏱️ Uptime: {uptime_str}\n🔄 Restarts: {bd['total_restarts']}",
                      chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        # ── RE-DETECT ──
        elif data.startswith("redetect:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "!")
            wd = bd['file_path'] if os.path.isdir(bd['file_path']) else user_folder(bd['user_id'])
            entry, ft, rp = det.report(wd)
            if entry:
                db.update_bot(bid, entry_file=entry, file_type=ft)
                m = types.InlineKeyboardMarkup(row_width=2)
                m.add(
                    types.InlineKeyboardButton("▶️ Start", callback_data=f"start:{bid}"),
                    types.InlineKeyboardButton("🔙 Back", callback_data=f"detail:{bid}")
                )
                safe_edit(f"🔍 <b>Re-Detection</b>\n\n{rp}\n\n✅ Entry updated!", chat_id, msg_id, reply_markup=m)
            else:
                af = [os.path.relpath(os.path.join(r, f), wd)
                      for r, d, fs in os.walk(wd) for f in fs if f.endswith(('.py', '.js'))]
                m = types.InlineKeyboardMarkup(row_width=1)
                for f in af[:10]:
                    ftype = 'js' if f.endswith('.js') else 'py'
                    m.add(types.InlineKeyboardButton(f"📄 {f}", callback_data=f"setentry:{bid}:{f}:{ftype}"))
                m.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"detail:{bid}"))
                t = "🔍 ❌ Auto-detect failed!\n\nSelect entry file:\n"
                for f in af[:10]:
                    t += f"• {f}\n"
                safe_edit(t, chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("setentry:"):
            parts = data.split(":")
            bid = int(parts[1])
            entry = parts[2]
            ft = parts[3]
            db.update_bot(bid, entry_file=entry, file_type=ft)
            safe_answer(call.id, f"✅ Entry: {entry}")
            call.data = f"detail:{bid}"
            handle_callback(call)

        # ── DELETE ──
        elif data.startswith("del:"):
            bid = int(data.split(":")[1])
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("✅ Yes Delete", callback_data=f"cdel:{bid}"),
                types.InlineKeyboardButton("❌ Cancel", callback_data=f"detail:{bid}")
            )
            safe_edit(f"🗑 <b>Delete Bot #{bid}?</b>\n\n⚠️ Cannot be undone!", chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("cdel:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if bd:
                sk = f"{bd['user_id']}_{bd['bot_name']}"
                if sk in bot_scripts:
                    kill_tree(bot_scripts[sk])
                    cleanup(sk)
                if os.path.isdir(bd['file_path']):
                    shutil.rmtree(bd['file_path'], ignore_errors=True)
                else:
                    try:
                        os.remove(os.path.join(user_folder(bd['user_id']), bd['bot_name']))
                    except:
                        pass
                db.del_bot(bid)
            safe_answer(call.id, "✅ Deleted!")
            call.data = "mybots"
            handle_callback(call)

        # ── DOWNLOAD ──
        elif data.startswith("dl:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "!")
            fp = os.path.join(bd['file_path'], bd['entry_file']) if os.path.isdir(bd['file_path']) else os.path.join(user_folder(bd['user_id']), bd['bot_name'])
            if os.path.exists(fp):
                try:
                    with open(fp, 'rb') as f:
                        bot.send_document(uid, f, caption=f"📄 {bd['bot_name']}")
                except:
                    pass
            safe_answer(call.id, "📥 Sent!")

        # ── DEPLOY ──
        elif data == "deploy":
            safe_answer(call.id)
            class M:
                def __init__(s, c):
                    s.chat = c.message.chat
                    s.from_user = c.from_user
            show_deploy(M(call))

        # ── REFERRAL ──
        elif data.startswith("cpref:"):
            rc = data.split(":", 1)[1]
            lnk = f"https://t.me/{BOT_USERNAME}?start={rc}"
            safe_answer(call.id)
            safe_send(uid, f"📋 <b>Your Referral Link:</b>\n\n<code>{lnk}</code>\n\n👆 Tap to copy!")

        elif data == "myrefs":
            refs = db.user_refs(uid)
            t = f"📋 <b>Your Referrals ({len(refs)})</b>\n\n"
            for r in refs[:20]:
                ru = db.get_user(r['referred_id'])
                name = ru['full_name'] if ru else str(r['referred_id'])
                t += f"👤 {name} — +{r['commission']} BDT — {r['created_at'][:10]}\n"
            if not refs:
                t += "No referrals yet!"
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu"))
            safe_edit(t, chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data == "board":
            lb = db.ref_board(10)
            t = f"🏆 <b>Referral Leaderboard</b>\n\n"
            medals = ['🥇', '🥈', '🥉']
            for i, l in enumerate(lb):
                icon = medals[i] if i < 3 else f"#{i + 1}"
                t += f"{icon} {l['full_name'] or '?'} — {l['referral_count']} refs ({l['referral_earnings']} BDT)\n"
            if not lb:
                t += "No referrals yet!"
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu"))
            safe_edit(t, chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        # ── PLANS & SUBSCRIPTION ──
        elif data in ("plans", "sub"):
            t = f"📋 <b>Available Plans</b>\n\n"
            for k, p in PLAN_LIMITS.items():
                if k == 'free':
                    continue
                bots_txt = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
                t += (f"{p['name']}\n"
                      f"  🤖 {bots_txt} bots | 💾 {p['ram']}MB RAM\n"
                      f"  🔄 Auto Restart: {'✅' if p['auto_restart'] else '❌'}\n"
                      f"  💰 {p['price']} BDT/month\n\n")
            safe_edit(t, chat_id, msg_id, reply_markup=plan_kb())
            safe_answer(call.id)

        elif data.startswith("plan:"):
            pk = data.split(":")[1]
            p = PLAN_LIMITS.get(pk)
            if not p:
                return
            bots_txt = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
            safe_edit(
                f"{p['name']}\n\n"
                f"🤖 Bots: {bots_txt}\n"
                f"💾 RAM: {p['ram']}MB\n"
                f"🔄 Auto Restart: {'✅' if p['auto_restart'] else '❌'}\n"
                f"💰 Price: {p['price']} BDT/month\n\n"
                f"Select payment method:",
                chat_id, msg_id, reply_markup=pay_method_kb(pk))
            safe_answer(call.id)

        elif data.startswith("pay:"):
            parts = data.split(":")
            pk = parts[1]
            mk = parts[2]
            p = PLAN_LIMITS.get(pk)
            pm = PAYMENT_METHODS.get(mk)
            if not p or not pm:
                return
            payment_states[uid] = {'step': 'wait_trx', 'plan': pk, 'method': mk, 'amount': p['price']}
            safe_edit(
                f"{pm['icon']} <b>{pm['name']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 Send to: <code>{pm['number']}</code>\n"
                f"📝 Type: {pm['type']}\n"
                f"💰 Amount: <b>{p['price']} BDT</b>\n"
                f"📦 Plan: {p['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📤 Send Transaction ID below:",
                chat_id, msg_id)
            safe_answer(call.id)

        elif data.startswith("payw:"):
            pk = data.split(":")[1]
            u = db.get_user(uid)
            p = PLAN_LIMITS.get(pk)
            if not u or not p:
                return
            if u['wallet_balance'] < p['price']:
                return safe_answer(call.id,
                    f"❌ Need: {p['price']} BDT | Have: {u['wallet_balance']} BDT",
                    show_alert=True)
            db.wallet_tx(uid, p['price'], 'purchase', f"Plan: {pk}")
            db.set_sub(uid, pk if pk != 'lifetime' else 'lifetime', 30)
            safe_answer(call.id, "✅ Plan activated!")
            safe_edit(f"✅ <b>Plan Activated!</b>\n\n📦 {p['name']}\n💰 Paid: {p['price']} BDT\n\n{BRAND_TAG}",
                      chat_id, msg_id)

        # ── PAYMENT APPROVAL ──
        elif data.startswith("appv:"):
            if uid not in admin_ids and uid != OWNER_ID:
                return
            pid = int(data.split(":")[1])
            p = db.approve_pay(pid, uid)
            if p:
                safe_answer(call.id, "✅ Approved!")
                safe_edit(
                    (call.message.text or '') + "\n\n✅ APPROVED",
                    chat_id, msg_id)
                plan_name = PLAN_LIMITS.get(p['plan'], {}).get('name', p['plan'])
                safe_send(p['user_id'],
                    f"🎉 <b>Payment Approved!</b>\n\n"
                    f"📦 Plan: {plan_name}\n"
                    f"📅 Duration: {p['duration_days']} days\n\n{BRAND_TAG}")

        elif data.startswith("rejt:"):
            if uid not in admin_ids and uid != OWNER_ID:
                return
            pid = int(data.split(":")[1])
            pay = db.get_pay(pid)
            db.reject_pay(pid, uid)
            safe_answer(call.id, "❌ Rejected!")
            safe_edit(
                (call.message.text or '') + "\n\n❌ REJECTED",
                chat_id, msg_id)
            if pay:
                safe_send(pay['user_id'],
                    f"❌ <b>Payment Rejected</b>\n\nPayment #{pid} not approved.\nContact {YOUR_USERNAME}\n\n{BRAND_TAG}")

        # ── SETTINGS ──
        elif data.startswith("lang:"):
            lang = data.split(":")[1]
            db.update_user(uid, language=lang)
            safe_answer(call.id, "✅ Language updated!")

        elif data == "profile":
            u = db.get_user(uid)
            if not u:
                return
            pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
            bc = db.bot_count(uid)
            lvl_icons = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💠', 'diamond': '💎'}
            safe_edit(
                f"👤 <b>MY PROFILE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📛 {u['full_name']}\n"
                f"🆔 <code>{uid}</code>\n"
                f"👤 @{u['username'] or 'N/A'}\n\n"
                f"📦 Plan: {pl['name']}\n"
                f"📅 Expires: {time_left(u['subscription_end'])}\n"
                f"🤖 Bots: {bc}\n"
                f"💰 Wallet: {u['wallet_balance']} BDT\n"
                f"💳 Spent: {u['total_spent']} BDT\n\n"
                f"👥 Refs: {u['referral_count']}\n"
                f"{lvl_icons.get(u['referral_level'], '🥉')} Level: {u['referral_level'].title()}\n"
                f"💰 Ref Earnings: {u['referral_earnings']} BDT\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id,
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Back", callback_data="menu")))
            safe_answer(call.id)

        elif data == "pay_history":
            pays = db.exe("SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
                          (uid,), fetch=True) or []
            t = "💳 <b>Payment History</b>\n\n"
            for p in pays:
                st_icon = "✅" if p['status'] == 'approved' else "❌" if p['status'] == 'rejected' else "⏳"
                t += f"{st_icon} #{p['payment_id']} — {p['amount']} BDT — {p['method']} — {p['status']}\n"
            if not pays:
                t += "No payments yet."
            safe_edit(t, chat_id, msg_id,
                      reply_markup=types.InlineKeyboardMarkup().add(
                          types.InlineKeyboardButton("🔙 Back", callback_data="menu")))
            safe_answer(call.id)

        # ── ADMIN ──
        elif data == "admin_back":
            safe_answer(call.id)
            s = db.stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            tickets = len(db.open_tickets())
            safe_edit(
                f"👑 <b>ADMIN PANEL</b>\n{BRAND_TAG}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 Users: {s['users']} (+{s['today']} today)\n"
                f"🤖 Running: {rn}\n"
                f"💎 Active Subs: {s['active_subs']}\n"
                f"💳 Pending: {s['pending']}\n"
                f"🎫 Tickets: {tickets}\n"
                f"💰 Revenue: {s['revenue']} BDT\n"
                f"Force Sub: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=admin_kb())

        elif data == "a_users":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            users = db.get_all_users()
            t = f"👥 <b>Users ({len(users)})</b>\n\n"
            for u in users[:25]:
                st = "🚫" if u['is_banned'] else "💎" if u['plan'] != 'free' else "✅"
                t += f"{st} <code>{u['user_id']}</code> {u['full_name'] or '-'} [{u['plan']}]\n"
            if len(users) > 25:
                t += f"\n... +{len(users) - 25} more"
            safe_send(uid, t[:4000])
            safe_answer(call.id)

        elif data == "a_stats":
            safe_answer(call.id)
            class M:
                def __init__(s, c):
                    s.chat = c.message.chat
                    s.from_user = c.from_user
            show_stats(M(call))

        elif data == "a_pay":
            safe_answer(call.id)
            class M:
                def __init__(s, c):
                    s.chat = c.message.chat
                    s.from_user = c.from_user
            show_payments(M(call))

        elif data == "a_bc":
            user_states[uid] = {'action': 'broadcast'}
            safe_answer(call.id)
            safe_send(uid, "📢 Send broadcast message:")

        elif data == "a_addsub":
            user_states[uid] = {'action': 'a_addsub', 'step': 1}
            safe_answer(call.id)
            safe_send(uid, "➕ Send user ID:")

        elif data.startswith("asub:"):
            parts = data.split(":")
            plan = parts[1]
            target = int(parts[2])
            user_states[uid] = {'action': 'a_addsub_days', 'target': target, 'plan': plan}
            safe_answer(call.id)
            safe_send(uid,
                f"📦 Plan: {PLAN_LIMITS[plan]['name']}\n"
                f"👤 User: <code>{target}</code>\n\n"
                f"Send days (0 = lifetime):")

        elif data == "a_remsub":
            user_states[uid] = {'action': 'a_remsub'}
            safe_answer(call.id)
            safe_send(uid, "➖ Send user ID to remove subscription:")

        elif data == "a_ban":
            user_states[uid] = {'action': 'a_ban'}
            safe_answer(call.id)
            safe_send(uid, "🚫 Send: USER_ID REASON")

        elif data == "a_unban":
            user_states[uid] = {'action': 'a_unban'}
            safe_answer(call.id)
            safe_send(uid, "✅ Send user ID to unban:")

        elif data == "a_promo":
            user_states[uid] = {'action': 'a_promo'}
            safe_answer(call.id)
            safe_send(uid, "🎟 Send: CODE DISCOUNT% MAX_USES\nEx: SAVE50 50 100")

        elif data == "a_channels":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            t = f"📢 <b>Force Subscribe Channels</b>\nStatus: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}\n\n"
            channels = db.get_all_channels()
            if channels:
                for ch in channels:
                    st = "🟢 Active" if ch['is_active'] else "🔴 Inactive"
                    t += f"• @{ch['channel_username']} — {ch['channel_name']}\n  {st}\n\n"
            else:
                t += "No channels. Default: @developer_apon_07\n"
            safe_edit(t, chat_id, msg_id, reply_markup=channels_kb())
            safe_answer(call.id)

        elif data.startswith("ch_toggle:"):
            if uid not in admin_ids and uid != OWNER_ID:
                return
            cid_ch = int(data.split(":")[1])
            new_status = db.toggle_channel(cid_ch)
            if new_status is not None:
                safe_answer(call.id, f"{'🟢 Activated' if new_status else '🔴 Deactivated'}")
            call.data = "a_channels"
            handle_callback(call)

        elif data == "ch_add":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            user_states[uid] = {'action': 'ch_add'}
            safe_answer(call.id)
            safe_send(uid, "➕ Send: @username Channel Name\nEx: @mychannel My Channel")

        elif data == "ch_remove":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            channels = db.get_active_channels()
            if not channels:
                safe_answer(call.id, "No channels!")
                return
            m = types.InlineKeyboardMarkup(row_width=1)
            for ch in channels:
                m.add(types.InlineKeyboardButton(f"🗑 @{ch['channel_username']}", callback_data=f"ch_del:{ch['channel_id']}"))
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data="a_channels"))
            safe_edit("🗑 Select channel to remove:", chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("ch_del:"):
            if uid not in admin_ids and uid != OWNER_ID:
                return
            cid_ch = int(data.split(":")[1])
            ch = db.exe("SELECT * FROM force_channels WHERE channel_id=?", (cid_ch,), one=True)
            if ch:
                db.delete_channel(cid_ch)
                safe_answer(call.id, f"✅ Deleted @{ch['channel_username']}")
            call.data = "a_channels"
            handle_callback(call)

        elif data == "a_fsub_toggle":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            FORCE_SUB_ENABLED = not FORCE_SUB_ENABLED
            safe_answer(call.id, f"Force Subscribe: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}")
            call.data = "admin_back"
            handle_callback(call)

        elif data == "a_tickets":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            tickets = db.open_tickets()
            t = f"🎫 <b>Open Tickets ({len(tickets)})</b>\n\n"
            m = types.InlineKeyboardMarkup(row_width=1)
            for tk in tickets[:10]:
                u = db.get_user(tk['user_id'])
                name = u['full_name'] if u else str(tk['user_id'])
                t += f"#{tk['ticket_id']} — {name}\n📝 {tk['message'][:50]}...\n\n"
                m.add(types.InlineKeyboardButton(f"💬 Reply #{tk['ticket_id']}", callback_data=f"tkt_reply:{tk['ticket_id']}"))
            if not tickets:
                t += "No open tickets! 🎉"
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
            safe_edit(t, chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("tkt_reply:"):
            if uid not in admin_ids and uid != OWNER_ID:
                return
            tid = int(data.split(":")[1])
            user_states[uid] = {'action': 'ticket_reply', 'ticket_id': tid}
            safe_answer(call.id)
            ticket = db.exe("SELECT * FROM tickets WHERE ticket_id=?", (tid,), one=True)
            if ticket:
                safe_send(uid, f"💬 <b>Reply to Ticket #{tid}</b>\n\n📝 {ticket['message'][:200]}\n\nSend reply:")

        elif data == "a_sys":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            ss = sys_stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_back"))
            safe_edit(
                f"🖥 <b>System</b>\n\n"
                f"🖥️ CPU: {ss['cpu']}%\n"
                f"🧠 RAM: {ss['mem']}%\n"
                f"💾 Disk: {ss['disk']}%\n"
                f"📊 RAM: {ss.get('mem_total', '?')}\n"
                f"💿 Disk: {ss.get('disk_total', '?')}\n"
                f"⏱️ Uptime: {ss['up']}\n"
                f"🤖 Running: {rn}",
                chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data == "a_stopall":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            count = 0
            for sk in list(bot_scripts.keys()):
                try:
                    kill_tree(bot_scripts[sk])
                    cleanup(sk)
                    count += 1
                except:
                    pass
            db.admin_log(uid, 'stop_all', details=f"stopped:{count}")
            safe_answer(call.id, f"🛑 Stopped {count} bots")

        elif data == "a_backup":
            if uid not in admin_ids and uid != OWNER_ID:
                return
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            bp = os.path.join(BACKUP_DIR, f"bk_{ts}.db")
            shutil.copy2(DB_PATH, bp)
            safe_answer(call.id, "💾 Backup created!")
            try:
                with open(bp, 'rb') as f:
                    bot.send_document(uid, f, caption=f"💾 Backup {ts}")
            except:
                pass

        elif data == "none":
            safe_answer(call.id)

        else:
            safe_answer(call.id)

    except Exception as e:
        logger.error(f"Callback [{data}]: {e}", exc_info=True)
        safe_answer(call.id, f"❌ Error!")


# ═══════════════════════════════════════════════════
#  CLEANUP
# ═══════════════════════════════════════════════════
def cleanup_all():
    logger.info("🛑 Shutting down...")
    count = 0
    for sk in list(bot_scripts.keys()):
        try:
            kill_tree(bot_scripts[sk])
            count += 1
        except:
            pass
    logger.info(f"🛑 Stopped {count} bots")

atexit.register(cleanup_all)


# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════
def main():
    logger.info("=" * 50)
    logger.info(f"  {BRAND} {BRAND_VER}")
    logger.info("=" * 50)

    # Seed default channels
    existing_channels = db.get_all_channels()
    if not existing_channels:
        for ch_user, ch_name in DEFAULT_FORCE_CHANNELS.items():
            db.add_channel(ch_user, ch_name, OWNER_ID)

    # Fix referral codes
    fixed = 0
    for u in db.get_all_users():
        rc = u.get('referral_code', '')
        if not rc or len(rc) < 5:
            try:
                db.update_user(u['user_id'], referral_code=gen_ref_code(u['user_id']))
                fixed += 1
            except:
                pass
    if fixed:
        logger.info(f"🔧 Fixed {fixed} referral codes")

    # Start threads
    threading.Thread(target=thread_monitor, daemon=True, name="Monitor").start()
    threading.Thread(target=thread_backup, daemon=True, name="Backup").start()
    threading.Thread(target=thread_expiry, daemon=True, name="Expiry").start()

    keep_alive()

    # Notify admins
    stats = db.stats()
    for aid in admin_ids:
        safe_send(aid,
            f"🚀 <b>{BRAND_SHORT} STARTED!</b>\n"
            f"{BRAND_TAG}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ All systems online\n"
            f"👥 Users: {stats['users']}\n"
            f"🤖 Bots: {stats['bots']}\n"
            f"💰 Revenue: {stats['revenue']} BDT\n"
            f"Force Sub: {'🟢 ON' if FORCE_SUB_ENABLED else '🔴 OFF'}\n"
            f"━━━━━━━━━━━━━━━━━━━━")

    logger.info("🟢 Bot READY!")

    # Polling with auto-reconnect
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30,
                                 allowed_updates=["message", "callback_query"])
        except requests.exceptions.ConnectionError:
            logger.error("🔴 Connection error! Retry 10s...")
            time.sleep(10)
        except requests.exceptions.ReadTimeout:
            logger.error("🔴 Timeout! Retry 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"🔴 Fatal: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()