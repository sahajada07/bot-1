"""
╔═══════════════════════════════════════════════════════════╗
║  🌟 APON HOSTING PANEL — Premium Edition v5.0 🌟         ║
║  Developer: @developer_apon                               ║
║  Complete Professional Rebuild                            ║
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
#  ERROR FORWARDING BOT SYSTEM
# ═══════════════════════════════════════════════════
ERROR_BOT_TOKEN = '8538355542:AAFZxITq12HB80-8M9i4xu6pHFaPUuzV4DI'
ERROR_CHAT_ID = None  # Will be set from OWNER_ID
error_bot = None

def init_error_bot():
    """Initialize the error forwarding bot"""
    global error_bot
    try:
        error_bot = telebot.TeleBot(ERROR_BOT_TOKEN, parse_mode='HTML')
        logger.info("✅ Error forwarding bot initialized")
    except Exception as e:
        logger.error(f"❌ Error bot init failed: {e}")

def forward_error(error_type, error_msg, user_id=None, extra=""):
    """Forward all errors to error monitoring bot"""
    global error_bot, ERROR_CHAT_ID
    if not error_bot or not ERROR_CHAT_ID:
        return
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text = (
            f"🚨 <b>ERROR REPORT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ Time: <code>{timestamp}</code>\n"
            f"🔴 Type: <code>{error_type}</code>\n"
            f"👤 User: <code>{user_id or 'System'}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Error:\n<code>{str(error_msg)[:1500]}</code>\n"
        )
        if extra:
            text += f"\n📎 Extra:\n<code>{str(extra)[:500]}</code>\n"
        text += f"\n━━━━━━━━━━━━━━━━━━━━\n🤖 {BRAND_TAG}"
        
        error_bot.send_message(ERROR_CHAT_ID, text)
    except Exception as e:
        logger.error(f"Error forwarding failed: {e}")

def forward_crash(func_name, exception, user_id=None):
    """Forward crash reports"""
    tb = traceback.format_exc()
    forward_error(
        f"CRASH in {func_name}",
        str(exception),
        user_id,
        tb[-500:]
    )

# ═══════════════════════════════════════════════════
#  FLASK KEEP-ALIVE
# ═══════════════════════════════════════════════════
flask_app = Flask('AponHosting')

@flask_app.route('/')
def flask_home():
    return "<h1>🌟 APON HOSTING PANEL 🌟</h1><p>Status: ✅ Online</p>"

@flask_app.route('/health')
def flask_health():
    return jsonify({
        "status": "ok", 
        "uptime": get_uptime(), 
        "version": "5.0",
        "running_bots": len([k for k in bot_scripts if is_running(k)])
    })

def keep_alive():
    Thread(
        target=lambda: flask_app.run(
            host='0.0.0.0', 
            port=int(os.environ.get("PORT", 8080))
        ), 
        daemon=True
    ).start()

# ═══════════════════════════════════════════════════
#  BRANDING
# ═══════════════════════════════════════════════════
BRAND = "🌟 APON HOSTING PANEL"
BRAND_SHORT = "AHP"
BRAND_VER = "v5.0"
BRAND_TAG = f"{BRAND} {BRAND_VER}"
BRAND_FOOTER = f"\n━━━━━━━━━━━━━━━━━━━━\n{BRAND_TAG}"

# ═══════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════
TOKEN = os.environ.get('BOT_TOKEN', '8258702948:AAHCT3iI934w6MnLle72GPUxQTR2O3z6aWA')
OWNER_ID = int(os.environ.get('OWNER_ID', '6678577936'))
ADMIN_ID = OWNER_ID
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'apon_vps_bot')
YOUR_USERNAME = '@developer_apon'
UPDATE_CHANNEL = 'https://t.me/developer_apon_07'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'upload_bots')
DATA_DIR = os.path.join(BASE_DIR, 'apon_data')
DB_PATH = os.path.join(DATA_DIR, 'apon.db')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')

DEFAULT_FORCE_CHANNELS = {'developer_apon_07': 'Developer Apon Updates'}

# ═══════════════════════════════════════════════════
#  GLOBAL STATE MANAGER
# ═══════════════════════════════════════════════════
class BotState:
    """Centralized state management"""
    def __init__(self):
        self.force_sub_enabled = True
        self.bot_locked = False
        self.bot_start_time = datetime.now()
        self.active_users = set()
        self.admin_ids = {ADMIN_ID, OWNER_ID}
        self.user_states = {}
        self.payment_states = {}
        self.user_msg_times = defaultdict(list)
        self.bot_scripts = {}
    
    def is_admin(self, uid):
        return uid == OWNER_ID or uid in self.admin_ids
    
    def set_state(self, uid, state_data):
        self.user_states[uid] = state_data
    
    def get_state(self, uid):
        return self.user_states.get(uid)
    
    def clear_state(self, uid):
        self.user_states.pop(uid, None)
        self.payment_states.pop(uid, None)
    
    def set_pay_state(self, uid, data):
        self.payment_states[uid] = data
    
    def get_pay_state(self, uid):
        return self.payment_states.get(uid)
    
    def clear_pay_state(self, uid):
        self.payment_states.pop(uid, None)

state = BotState()
bot_scripts = state.bot_scripts

# ═══════════════════════════════════════════════════
#  PLAN CONFIGURATION
# ═══════════════════════════════════════════════════
PLAN_LIMITS = {
    'free':       {'name': '🆓 Free',        'max_bots': 1,  'ram': 128,  'auto_restart': False, 'price': 0},
    'starter':    {'name': '🟢 Starter',     'max_bots': 2,  'ram': 256,  'auto_restart': True,  'price': 99},
    'basic':      {'name': '⭐ Basic',        'max_bots': 5,  'ram': 512,  'auto_restart': True,  'price': 199},
    'pro':        {'name': '💎 Pro',          'max_bots': 15, 'ram': 2048, 'auto_restart': True,  'price': 499},
    'enterprise': {'name': '🏢 Enterprise',   'max_bots': 50, 'ram': 4096, 'auto_restart': True,  'price': 999},
    'lifetime':   {'name': '👑 Lifetime',     'max_bots': -1, 'ram': 8192, 'auto_restart': True,  'price': 1999},
}

PAYMENT_METHODS = {
    'bkash':   {'name': 'bKash',       'number': '01306633616',            'type': 'Send Money',       'icon': '🟪'},
    'nagad':   {'name': 'Nagad',       'number': '01306633616',            'type': 'Send Money',       'icon': '🟧'},
    'rocket':  {'name': 'Rocket',      'number': '01306633616',            'type': 'Send Money',       'icon': '🟦'},
    'upay':    {'name': 'Upay',        'number': '01306633616',            'type': 'Send Money',       'icon': '🟩'},
    'binance': {'name': 'Binance Pay', 'number': 'Binance ID: 758637628', 'type': 'Binance Pay/USDT', 'icon': '🟡'},
    'bank':    {'name': 'Bank',        'number': 'Contact Admin',          'type': 'Transfer',         'icon': '🏦'},
}

REF_BONUS_DAYS = 3
REF_COMMISSION = 20

MODULES_MAP = {
    'telebot': 'pytelegrambotapi', 'telegram': 'python-telegram-bot',
    'pyrogram': 'pyrogram', 'telethon': 'telethon', 'aiogram': 'aiogram',
    'PIL': 'Pillow', 'cv2': 'opencv-python', 'sklearn': 'scikit-learn',
    'bs4': 'beautifulsoup4', 'dotenv': 'python-dotenv', 'yaml': 'pyyaml',
    'aiohttp': 'aiohttp', 'numpy': 'numpy', 'pandas': 'pandas',
    'requests': 'requests', 'flask': 'flask', 'fastapi': 'fastapi',
    'motor': 'motor', 'pymongo': 'pymongo', 'httpx': 'httpx',
    'cryptography': 'cryptography',
}

# ═══════════════════════════════════════════════════
#  DIRECTORY SETUP
# ═══════════════════════════════════════════════════
for _d in [UPLOAD_DIR, DATA_DIR, LOGS_DIR, BACKUP_DIR]:
    os.makedirs(_d, exist_ok=True)

# ═══════════════════════════════════════════════════
#  LOGGING SETUP
# ═══════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'apon.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('APON')

# ═══════════════════════════════════════════════════
#  BOT INITIALIZATION
# ═══════════════════════════════════════════════════
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# ═══════════════════════════════════════════════════
#  SAFE MESSAGE FUNCTIONS (Zero Crash)
# ═══════════════════════════════════════════════════
def safe_send(chat_id, text, **kwargs):
    """Send message with complete error handling and forwarding"""
    try:
        kwargs.setdefault('parse_mode', 'HTML')
        return bot.send_message(chat_id, text, **kwargs)
    except telebot.apihelper.ApiTelegramException as e:
        err_str = str(e).lower()
        if 'can\'t parse' in err_str or 'bad request' in err_str:
            try:
                kwargs.pop('parse_mode', None)
                return bot.send_message(chat_id, text, **kwargs)
            except Exception as e2:
                forward_error("SEND_MSG_FALLBACK", e2, chat_id)
                return None
        elif 'bot was blocked' in err_str or 'user is deactivated' in err_str:
            logger.info(f"User {chat_id} blocked/deactivated")
            return None
        else:
            forward_error("SEND_MSG_API", e, chat_id)
            logger.warning(f"API Error -> {chat_id}: {e}")
            return None
    except Exception as e:
        forward_error("SEND_MSG", e, chat_id)
        logger.error(f"Send error: {e}")
        return None


def safe_edit(text, chat_id, msg_id, **kwargs):
    """Edit message with complete error handling"""
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
            except Exception as e2:
                forward_error("EDIT_MSG_FALLBACK", e2, chat_id)
                return None
        if 'message to edit not found' in err:
            return safe_send(chat_id, text, **kwargs)
        forward_error("EDIT_MSG_API", e, chat_id)
        return None
    except Exception as e:
        forward_error("EDIT_MSG", e, chat_id)
        return None


def safe_delete(chat_id, msg_id):
    """Delete message safely"""
    try:
        bot.delete_message(chat_id, msg_id)
        return True
    except:
        return False


def safe_answer(call_id, text="", **kwargs):
    """Answer callback with error handling"""
    try:
        bot.answer_callback_query(call_id, text, **kwargs)
    except:
        pass


def safe_reply(msg, text, **kwargs):
    """Reply to message safely"""
    try:
        kwargs.setdefault('parse_mode', 'HTML')
        return bot.reply_to(msg, text, **kwargs)
    except:
        return safe_send(msg.chat.id, text, **kwargs)

# ═══════════════════════════════════════════════════
#  RATE LIMITER
# ═══════════════════════════════════════════════════
def rate_check(uid):
    now = time.time()
    times = state.user_msg_times[uid]
    state.user_msg_times[uid] = [t for t in times if now - t < 60]
    if len(state.user_msg_times[uid]) >= 30:
        return False
    if state.user_msg_times[uid] and now - state.user_msg_times[uid][-1] < 0.3:
        return False
    state.user_msg_times[uid].append(now)
    return True

# ═══════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════
def get_uptime():
    d = datetime.now() - state.bot_start_time
    h, r = divmod(d.seconds, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d.days:
        parts.append(f"{d.days}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m {s}s")
    return " ".join(parts)


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


def cleanup_script(sk):
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
            'mem_used': fmt_size(m.used),
            'disk_total': fmt_size(d.total),
            'disk_used': fmt_size(d.used),
        }
    except:
        return {
            'cpu': 0, 'mem': 0, 'disk': 0, 'up': get_uptime(),
            'mem_total': '?', 'mem_used': '?',
            'disk_total': '?', 'disk_used': '?'
        }


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
#  FORCE SUBSCRIBE SYSTEM
# ═══════════════════════════════════════════════════
def check_joined(uid):
    if not state.force_sub_enabled:
        return True, []
    if state.is_admin(uid):
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
        m.add(types.InlineKeyboardButton(
            f"📢 Join {cn}", url=f"https://t.me/{cu}"
        ))
    m.add(types.InlineKeyboardButton(
        "✅ I've Joined — Verify", callback_data="verify_join"
    ))
    return m


def send_force_sub(cid, nj):
    ch_text = ""
    for i, (cu, cn) in enumerate(nj, 1):
        ch_text += f"  {i}. <b>{cn}</b> — @{cu}\n"
    safe_send(cid,
        f"🔒 <b>CHANNEL VERIFICATION REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ You must join our channels to use this bot!\n\n"
        f"{ch_text}\n"
        f"👇 Join all channels, then press <b>Verify</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=force_sub_kb(nj))

# ═══════════════════════════════════════════════════
#  SMART ENTRY FILE DETECTOR
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

        indicators_py = ['infinity_polling', 'polling()', 'bot.polling', 'app.run(', 'if __name__', 'telebot.TeleBot', 'Bot(token']
        for rp, fp in pyf:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    c = f.read(5000)
                if sum(1 for x in indicators_py if x in c) >= 2:
                    return rp, 'py', 'medium'
            except:
                pass

        indicators_js = ['require(', 'app.listen', 'bot.launch', 'client.login', 'express()']
        for rp, fp in jsf:
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                    c = f.read(5000)
                if sum(1 for x in indicators_js if x in c) >= 2:
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
                safe_send(cid, "📦 Installing requirements.txt...")
            try:
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '-r', r, '--quiet'],
                    capture_output=True, text=True, timeout=300, cwd=d
                )
            except Exception as e:
                forward_error("INSTALL_REQ", e)
        return True

    @staticmethod
    def install_npm(d, cid=None):
        if os.path.exists(os.path.join(d, 'package.json')) and not os.path.exists(os.path.join(d, 'node_modules')):
            if cid:
                safe_send(cid, "📦 Running npm install...")
            try:
                subprocess.run(
                    ['npm', 'install', '--production'],
                    capture_output=True, text=True, timeout=300, cwd=d
                )
            except Exception as e:
                forward_error("INSTALL_NPM", e)
        return True

    @staticmethod
    def report(d):
        e, ft, cf = Detector.detect(d)
        if not e:
            return None, None, "❌ No runnable file detected!"
        ci = {'exact': '🎯 Exact Match', 'high': '✅ High', 'medium': '🟡 Medium', 'low': '⚠️ Low'}
        ti = {'py': '🐍 Python', 'js': '🟨 Node.js'}
        return e, ft, (
            f"📄 Entry: <code>{e}</code>\n"
            f"🔤 Type: {ti.get(ft, ft)}\n"
            f"🎯 Confidence: {ci.get(cf, cf)}"
        )


det = Detector()

# ═══════════════════════════════════════════════════
#  DATABASE — Complete with All Tables
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
        c.execute("PRAGMA busy_timeout=5000")
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
                logger.error(f"DB Error: {e} | Query: {q[:100]}")
                forward_error("DATABASE", e, extra=q[:200])
                return None

    def _init(self):
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

        self.exe("""CREATE TABLE IF NOT EXISTS referrals(
            ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            bonus_days INTEGER DEFAULT 0,
            commission REAL DEFAULT 0,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        self.exe("""CREATE TABLE IF NOT EXISTS wallet_tx(
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tx_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        self.exe("""CREATE TABLE IF NOT EXISTS admin_logs(
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user INTEGER,
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        self.exe("""CREATE TABLE IF NOT EXISTS force_channels(
            channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE NOT NULL,
            channel_name TEXT DEFAULT '',
            added_by INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        self.exe("""CREATE TABLE IF NOT EXISTS tickets(
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            admin_reply TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        self.exe("""CREATE TABLE IF NOT EXISTS notifications(
            notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Notification',
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT(datetime('now'))
        )""")

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

        self.exe("""CREATE TABLE IF NOT EXISTS error_logs(
            error_id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            user_id INTEGER,
            traceback_info TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now'))
        )""")

        logger.info("✅ All DB tables initialized")

    # ── User Methods ──
    def get_user(self, uid):
        return self.exe("SELECT * FROM users WHERE user_id=?", (uid,), one=True)

    def create_user(self, uid, un='', fn='', rc='', rb=None):
        self.exe(
            "INSERT OR IGNORE INTO users(user_id,username,full_name,referral_code,referred_by) VALUES(?,?,?,?,?)",
            (uid, un, fn, rc, rb)
        )

    def update_user(self, uid, **kw):
        if not kw:
            return
        cols = ','.join(f'{k}=?' for k in kw)
        vals = list(kw.values()) + [uid]
        self.exe(f"UPDATE users SET {cols} WHERE user_id=?", vals)

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
            end = (datetime.now() + timedelta(days=days)).isoformat()
            self.update_user(uid, plan=plan, is_lifetime=0, subscription_end=end)

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
        if state.is_admin(uid):
            return PLAN_LIMITS['lifetime']
        return PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])

    # ── Bot Methods ──
    def add_bot(self, uid, name, path, entry='main.py', ft='py', tok='', sz=0, conf=''):
        return self.exe(
            "INSERT INTO bots(user_id,bot_name,file_path,entry_file,file_type,bot_token,file_size,detection_confidence) VALUES(?,?,?,?,?,?,?,?)",
            (uid, name, path, entry, ft, tok, sz, conf)
        )

    def get_bots(self, uid):
        return self.exe("SELECT * FROM bots WHERE user_id=?", (uid,), fetch=True) or []

    def get_bot(self, bid):
        return self.exe("SELECT * FROM bots WHERE bot_id=?", (bid,), one=True)

    def update_bot(self, bid, **kw):
        if not kw:
            return
        cols = ','.join(f'{k}=?' for k in kw)
        vals = list(kw.values()) + [bid]
        self.exe(f"UPDATE bots SET {cols} WHERE bot_id=?", vals)

    def del_bot(self, bid):
        self.exe("DELETE FROM bots WHERE bot_id=?", (bid,))

    def bot_count(self, uid):
        r = self.exe("SELECT COUNT(*) as c FROM bots WHERE user_id=?", (uid,), one=True)
        return r['c'] if r else 0

    # ── Payment Methods ──
    def add_pay(self, uid, amt, method, trx, plan, days=30):
        return self.exe(
            "INSERT INTO payments(user_id,amount,method,transaction_id,plan,duration_days) VALUES(?,?,?,?,?,?)",
            (uid, amt, method, trx, plan, days)
        )

    def pending_pay(self):
        return self.exe(
            "SELECT * FROM payments WHERE status='pending' ORDER BY created_at DESC",
            fetch=True
        ) or []

    def get_pay(self, pid):
        return self.exe("SELECT * FROM payments WHERE payment_id=?", (pid,), one=True)

    def user_payments(self, uid, limit=10):
        return self.exe(
            "SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (uid, limit), fetch=True
        ) or []

    def approve_pay(self, pid, aid):
        p = self.get_pay(pid)
        if not p:
            return None
        self.exe(
            "UPDATE payments SET status='approved',approved_by=?,processed_at=datetime('now') WHERE payment_id=?",
            (aid, pid)
        )
        self.set_sub(p['user_id'], p['plan'], p['duration_days'])
        self.update_user(p['user_id'], total_spent=self.get_user(p['user_id']).get('total_spent', 0) + p['amount'])
        return p

    def reject_pay(self, pid, aid):
        self.exe(
            "UPDATE payments SET status='rejected',approved_by=?,processed_at=datetime('now') WHERE payment_id=?",
            (aid, pid)
        )

    # ── Referral Methods ──
    def add_ref(self, rr, rd, days=3, comm=20):
        self.exe(
            "INSERT INTO referrals(referrer_id,referred_id,bonus_days,commission) VALUES(?,?,?,?)",
            (rr, rd, days, comm)
        )
        u = self.get_user(rr)
        if u:
            nc = u['referral_count'] + 1
            lv = 'diamond' if nc >= 100 else 'platinum' if nc >= 50 else 'gold' if nc >= 25 else 'silver' if nc >= 10 else 'bronze'
            self.update_user(
                rr,
                referral_count=nc,
                referral_earnings=u['referral_earnings'] + comm,
                wallet_balance=u['wallet_balance'] + comm,
                referral_level=lv
            )
            self.wallet_tx(rr, comm, 'referral', f"Referral bonus: User {rd}")

    def ref_board(self, lim=10):
        return self.exe(
            "SELECT * FROM users ORDER BY referral_count DESC LIMIT ?",
            (lim,), fetch=True
        ) or []

    def user_refs(self, uid):
        return self.exe(
            "SELECT * FROM referrals WHERE referrer_id=? ORDER BY created_at DESC",
            (uid,), fetch=True
        ) or []

    # ── Wallet Methods ──
    def wallet_tx(self, uid, amt, tt, desc=''):
        self.exe(
            "INSERT INTO wallet_tx(user_id,amount,tx_type,description) VALUES(?,?,?,?)",
            (uid, amt, tt, desc)
        )
        if tt in ('credit', 'referral', 'refund', 'bonus'):
            self.exe("UPDATE users SET wallet_balance=wallet_balance+? WHERE user_id=?", (amt, uid))
        elif tt in ('debit', 'withdraw', 'purchase'):
            self.exe("UPDATE users SET wallet_balance=wallet_balance-? WHERE user_id=?", (amt, uid))

    def wallet_hist(self, uid, lim=20):
        return self.exe(
            "SELECT * FROM wallet_tx WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (uid, lim), fetch=True
        ) or []

    # ── Force Channel Methods ──
    def add_channel(self, username, name='', added_by=None):
        username = username.strip().lstrip('@').lower()
        ex = self.exe("SELECT * FROM force_channels WHERE channel_username=?", (username,), one=True)
        if ex:
            self.exe("UPDATE force_channels SET is_active=1,channel_name=? WHERE channel_username=?",
                     (name or username, username))
            return ex['channel_id']
        return self.exe(
            "INSERT INTO force_channels(channel_username,channel_name,added_by) VALUES(?,?,?)",
            (username, name or username, added_by)
        )

    def remove_channel(self, username):
        self.exe(
            "UPDATE force_channels SET is_active=0 WHERE channel_username=?",
            (username.strip().lstrip('@').lower(),)
        )

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

    # ── Ticket Methods ──
    def add_ticket(self, uid, subj, msg):
        return self.exe("INSERT INTO tickets(user_id,subject,message) VALUES(?,?,?)", (uid, subj, msg))

    def open_tickets(self):
        return self.exe(
            "SELECT * FROM tickets WHERE status='open' ORDER BY created_at DESC",
            fetch=True
        ) or []

    def get_ticket(self, tid):
        return self.exe("SELECT * FROM tickets WHERE ticket_id=?", (tid,), one=True)

    def reply_ticket(self, tid, reply):
        self.exe("UPDATE tickets SET admin_reply=?,status='replied' WHERE ticket_id=?", (reply, tid))

    # ── Notification Methods ──
    def add_notif(self, uid, title, message):
        return self.exe("INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)", (uid, title, message))

    def get_notifs(self, uid, lim=10):
        return self.exe(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (uid, lim), fetch=True
        ) or []

    def unread_count(self, uid):
        r = self.exe("SELECT COUNT(*) as c FROM notifications WHERE user_id=? AND is_read=0", (uid,), one=True)
        return r['c'] if r else 0

    def mark_read(self, uid):
        self.exe("UPDATE notifications SET is_read=1 WHERE user_id=?", (uid,))

    # ── Promo Methods ──
    def get_promo(self, code):
        return self.exe("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code.upper(),), one=True)

    def use_promo(self, code):
        self.exe("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code.upper(),))

    def add_promo(self, code, discount, max_uses, created_by):
        return self.exe(
            "INSERT OR IGNORE INTO promo_codes(code,discount_pct,max_uses,created_by) VALUES(?,?,?,?)",
            (code.upper(), discount, max_uses, created_by)
        )

    def all_promos(self):
        return self.exe("SELECT * FROM promo_codes ORDER BY created_at DESC", fetch=True) or []

    # ── Error Log ──
    def log_error(self, error_type, error_msg, uid=None, tb=''):
        self.exe(
            "INSERT INTO error_logs(error_type,error_message,user_id,traceback_info) VALUES(?,?,?,?)",
            (error_type, str(error_msg)[:500], uid, tb[:1000])
        )

    # ── Admin Log ──
    def admin_log(self, aid, act, tgt=None, det=''):
        self.exe(
            "INSERT INTO admin_logs(admin_id,action,target_user,details) VALUES(?,?,?,?)",
            (aid, act, tgt, det)
        )

    def get_admin_logs(self, limit=20):
        return self.exe(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?",
            (limit,), fetch=True
        ) or []

    # ── Statistics ──
    def stats(self):
        tu = (self.exe("SELECT COUNT(*) as c FROM users", one=True) or {}).get('c', 0)
        tb = (self.exe("SELECT COUNT(*) as c FROM bots", one=True) or {}).get('c', 0)
        pp = (self.exe("SELECT COUNT(*) as c FROM payments WHERE status='pending'", one=True) or {}).get('c', 0)
        rv = (self.exe("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='approved'", one=True) or {}).get('s', 0)
        td = (self.exe("SELECT COUNT(*) as c FROM users WHERE date(created_at)=date('now')", one=True) or {}).get('c', 0)
        ac = (self.exe("SELECT COUNT(*) as c FROM users WHERE plan!='free' AND(is_lifetime=1 OR subscription_end>datetime('now'))", one=True) or {}).get('c', 0)
        bn = (self.exe("SELECT COUNT(*) as c FROM users WHERE is_banned=1", one=True) or {}).get('c', 0)
        return {
            'users': tu, 'bots': tb, 'pending': pp, 'revenue': rv,
            'today': td, 'active_subs': ac, 'banned': bn
        }


db = DB()

# ═══════════════════════════════════════════════════
#  ALL KEYBOARD BUILDERS
# ═══════════════════════════════════════════════════

def main_menu_kb(uid):
    """Main menu — always inline buttons"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🤖 My Bots", callback_data="menu_mybots"),
        types.InlineKeyboardButton("📤 Deploy Bot", callback_data="menu_deploy")
    )
    m.add(
        types.InlineKeyboardButton("💎 Subscription", callback_data="menu_sub"),
        types.InlineKeyboardButton("💰 Wallet", callback_data="menu_wallet")
    )
    m.add(
        types.InlineKeyboardButton("🎁 Referral", callback_data="menu_ref"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="menu_stats")
    )
    m.add(
        types.InlineKeyboardButton("🟢 Running Bots", callback_data="menu_running"),
        types.InlineKeyboardButton("⚡ Speed Test", callback_data="menu_speed")
    )
    m.add(
        types.InlineKeyboardButton("📚 Help", callback_data="menu_help"),
        types.InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
    )
    
    notif_count = db.unread_count(uid)
    notif_label = f"🔔 Notifications ({notif_count})" if notif_count > 0 else "🔔 Notifications"
    m.add(
        types.InlineKeyboardButton(notif_label, callback_data="menu_notif"),
        types.InlineKeyboardButton("🎫 Support", callback_data="menu_support")
    )
    
    if state.is_admin(uid):
        m.add(types.InlineKeyboardButton("👑 Admin Panel", callback_data="menu_admin"))
    
    m.add(types.InlineKeyboardButton("📞 Contact Developer", url=f"https://t.me/developer_apon"))
    return m


def help_menu_kb():
    """Help menu — ALL options as inline buttons"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📤 How to Deploy", callback_data="help_deploy"),
        types.InlineKeyboardButton("🤖 Managing Bots", callback_data="help_bots")
    )
    m.add(
        types.InlineKeyboardButton("💎 Plans & Pricing", callback_data="help_plans"),
        types.InlineKeyboardButton("💳 Payment Guide", callback_data="help_payment")
    )
    m.add(
        types.InlineKeyboardButton("🎁 Referral System", callback_data="help_referral"),
        types.InlineKeyboardButton("💰 Wallet Guide", callback_data="help_wallet")
    )
    m.add(
        types.InlineKeyboardButton("🔍 Auto Detection", callback_data="help_detect"),
        types.InlineKeyboardButton("📦 Supported Files", callback_data="help_files")
    )
    m.add(
        types.InlineKeyboardButton("❓ FAQ", callback_data="help_faq"),
        types.InlineKeyboardButton("🛠 Troubleshoot", callback_data="help_trouble")
    )
    m.add(
        types.InlineKeyboardButton("📋 All Commands", callback_data="help_commands"),
        types.InlineKeyboardButton("📞 Contact Support", callback_data="help_contact")
    )
    m.add(types.InlineKeyboardButton("🏠 Back to Main Menu", callback_data="go_home"))
    return m


def back_btn(cb="go_home", text="🏠 Main Menu"):
    """Single back button"""
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(text, callback_data=cb))
    return m


def back_help_btn():
    """Back to help menu"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("📚 Back to Help", callback_data="menu_help"),
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )
    return m


def bot_action_kb(bid, is_live):
    """Bot control buttons"""
    m = types.InlineKeyboardMarkup(row_width=2)
    if is_live:
        m.add(
            types.InlineKeyboardButton("🛑 Stop", callback_data=f"bot_stop:{bid}"),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f"bot_restart:{bid}")
        )
        m.add(
            types.InlineKeyboardButton("📋 Logs", callback_data=f"bot_logs:{bid}"),
            types.InlineKeyboardButton("📊 Resources", callback_data=f"bot_res:{bid}")
        )
    else:
        m.add(
            types.InlineKeyboardButton("▶️ Start", callback_data=f"bot_start:{bid}"),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f"bot_del:{bid}")
        )
        m.add(
            types.InlineKeyboardButton("📋 Logs", callback_data=f"bot_logs:{bid}"),
            types.InlineKeyboardButton("📥 Download", callback_data=f"bot_dl:{bid}")
        )
        m.add(types.InlineKeyboardButton("🔍 Re-detect Entry", callback_data=f"bot_redetect:{bid}"))
    m.add(types.InlineKeyboardButton("🔙 Back to My Bots", callback_data="menu_mybots"))
    return m


def plan_kb():
    """Plans selection"""
    m = types.InlineKeyboardMarkup(row_width=1)
    for k, p in PLAN_LIMITS.items():
        if k == 'free':
            continue
        slots = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
        m.add(types.InlineKeyboardButton(
            f"{p['name']} — {slots} bots — {p['price']} BDT",
            callback_data=f"plan_select:{k}"
        ))
    m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
    return m


def pay_method_kb(pk):
    """Payment method selection"""
    m = types.InlineKeyboardMarkup(row_width=2)
    for k, v in PAYMENT_METHODS.items():
        m.add(types.InlineKeyboardButton(
            f"{v['icon']} {v['name']}",
            callback_data=f"pay_method:{pk}:{k}"
        ))
    m.add(types.InlineKeyboardButton("💰 Pay from Wallet", callback_data=f"pay_wallet:{pk}"))
    m.add(
        types.InlineKeyboardButton("🔙 Back to Plans", callback_data="menu_sub"),
        types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
    )
    return m


def admin_kb():
    """Admin panel buttons"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("👥 All Users", callback_data="adm_users"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="adm_stats")
    )
    m.add(
        types.InlineKeyboardButton("💳 Pending Payments", callback_data="adm_payments"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")
    )
    m.add(
        types.InlineKeyboardButton("➕ Add Subscription", callback_data="adm_addsub"),
        types.InlineKeyboardButton("➖ Remove Subscription", callback_data="adm_remsub")
    )
    m.add(
        types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="adm_unban")
    )
    m.add(
        types.InlineKeyboardButton("📢 Force Sub Channels", callback_data="adm_channels"),
        types.InlineKeyboardButton("🎟 Promo Codes", callback_data="adm_promo")
    )
    m.add(
        types.InlineKeyboardButton("🎫 Support Tickets", callback_data="adm_tickets"),
        types.InlineKeyboardButton("🖥 System Info", callback_data="adm_system")
    )
    m.add(
        types.InlineKeyboardButton("🛑 Stop All Bots", callback_data="adm_stopall"),
        types.InlineKeyboardButton("💾 Backup DB", callback_data="adm_backup")
    )
    m.add(
        types.InlineKeyboardButton("📜 Admin Logs", callback_data="adm_logs"),
        types.InlineKeyboardButton("💰 Give Balance", callback_data="adm_give")
    )
    m.add(
        types.InlineKeyboardButton("🔍 User Info", callback_data="adm_userinfo"),
        types.InlineKeyboardButton("🔔 Send Notification", callback_data="adm_notify")
    )
    
    fsub_icon = "🟢" if state.force_sub_enabled else "🔴"
    lock_icon = "🔒" if state.bot_locked else "🔓"
    m.add(
        types.InlineKeyboardButton(f"{fsub_icon} Force Subscribe", callback_data="adm_fsub_toggle"),
        types.InlineKeyboardButton(f"{lock_icon} Bot Lock", callback_data="adm_lock_toggle")
    )
    m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
    return m


def pay_approve_kb(pid):
    """Payment approve/reject"""
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve:{pid}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"pay_reject:{pid}")
    )
    return m


def channels_manage_kb():
    """Channel management"""
    channels = db.get_all_channels()
    m = types.InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        icon = "🟢" if ch['is_active'] else "🔴"
        m.add(types.InlineKeyboardButton(
            f"{icon} @{ch['channel_username']} — {ch['channel_name']}",
            callback_data=f"ch_toggle:{ch['channel_id']}"
        ))
    m.add(types.InlineKeyboardButton("➕ Add Channel", callback_data="ch_add"))
    m.add(types.InlineKeyboardButton("🗑 Remove Channel", callback_data="ch_remove"))
    m.add(types.InlineKeyboardButton("🔙 Back to Admin", callback_data="menu_admin"))
    return m


# ═══════════════════════════════════════════════════
#  SCRIPT RUNNER ENGINE
# ═══════════════════════════════════════════════════
def pip_install(mod, cid):
    pkg = MODULES_MAP.get(mod.split('.')[0].lower(), mod)
    try:
        safe_send(cid, f"📦 Installing <code>{pkg}</code>...")
        r = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            safe_send(cid, f"✅ Installed <code>{pkg}</code>")
            return True
        return False
    except Exception as e:
        forward_error("PIP_INSTALL", e)
        return False


def run_bot_script(bid, cid, att=1):
    """Run a bot script with complete error handling"""
    if att > 3:
        safe_send(cid, "❌ <b>Failed after 3 attempts!</b>\nCheck your code for errors.")
        return

    bd = db.get_bot(bid)
    if not bd:
        safe_send(cid, "❌ Bot not found in database!")
        return

    uid = bd['user_id']
    bn = bd['bot_name']
    fp = bd['file_path']
    ef = bd['entry_file']
    ft = bd['file_type']
    sk = f"{uid}_{bn}"
    wd = fp if os.path.isdir(fp) else user_folder(uid)

    try:
        # Re-detect entry on first attempt
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
                af = [
                    os.path.relpath(os.path.join(r, f), wd)
                    for r, d, fs in os.walk(wd) for f in fs
                    if f.endswith(('.py', '.js'))
                ]
                err = f"❌ <b>Entry file not found:</b> <code>{ef}</code>\n\n📁 Available files:\n"
                for f in af[:10]:
                    err += f"  • <code>{f}</code>\n"
                if not af:
                    err += "  (No .py or .js files found)"
                m = types.InlineKeyboardMarkup()
                m.add(types.InlineKeyboardButton("🔍 Re-detect", callback_data=f"bot_redetect:{bid}"))
                m.add(types.InlineKeyboardButton("🔙 My Bots", callback_data="menu_mybots"))
                safe_send(cid, err, reply_markup=m)
                return

        # Install dependencies
        if att == 1:
            if ft == 'py':
                det.install_req(wd, cid)
            else:
                det.install_npm(wd, cid)

        type_icon = '🐍 Python' if ft == 'py' else '🟨 Node.js'
        safe_send(cid,
            f"🚀 <b>Starting Bot...</b>\n\n"
            f"📄 <code>{ef}</code>\n"
            f"🔤 {type_icon}\n"
            f"🔄 Attempt: {att}/3"
        )

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

        # Wait and check
        time.sleep(5)
        if proc.poll() is None:
            time.sleep(3)
            if proc.poll() is None:
                db.update_bot(
                    bid, status='running', pid=proc.pid,
                    last_started=datetime.now().isoformat(),
                    entry_file=ef, file_type=ft
                )
                m = types.InlineKeyboardMarkup(row_width=2)
                m.add(
                    types.InlineKeyboardButton("🛑 Stop", callback_data=f"bot_stop:{bid}"),
                    types.InlineKeyboardButton("📋 Logs", callback_data=f"bot_logs:{bid}")
                )
                m.add(types.InlineKeyboardButton("🔙 My Bots", callback_data="menu_mybots"))
                safe_send(cid,
                    f"✅ <b>BOT IS RUNNING!</b>\n\n"
                    f"📄 <code>{ef}</code>\n"
                    f"🆔 PID: <code>{proc.pid}</code>\n"
                    f"🔤 {type_icon}\n"
                    f"⏱️ {datetime.now().strftime('%H:%M:%S')}\n"
                    f"📊 Status: 🟢 Running",
                    reply_markup=m
                )
                return

        # Bot crashed — read error
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
            cleanup_script(sk)
            if pip_install(match.group(1).split('.')[0], cid):
                time.sleep(1)
                run_bot_script(bid, cid, att + 1)
                return

        # Auto-install missing npm module
        match = re.search(r"Cannot find module '([^']+)'", err)
        if match and not match.group(1).startswith('.'):
            cleanup_script(sk)
            try:
                subprocess.run(['npm', 'install', match.group(1)],
                               cwd=wd, capture_output=True, timeout=60)
                time.sleep(1)
                run_bot_script(bid, cid, att + 1)
                return
            except:
                pass

        # Try alternate entry
        if att == 1:
            alts = ['app.py', 'main.py', 'bot.py', 'run.py', 'index.js', 'app.js']
            for alt in alts:
                if os.path.exists(os.path.join(wd, alt)) and alt != ef:
                    cleanup_script(sk)
                    db.update_bot(bid, entry_file=alt,
                                  file_type='js' if alt.endswith('.js') else 'py')
                    run_bot_script(bid, cid, att + 1)
                    return

        # Show final error
        err_display = err[-500:] if err.strip() else 'No output captured'
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("🔄 Retry", callback_data=f"bot_start:{bid}"),
            types.InlineKeyboardButton("📋 Full Logs", callback_data=f"bot_logs:{bid}")
        )
        m.add(types.InlineKeyboardButton("🔙 My Bots", callback_data="menu_mybots"))
        safe_send(cid,
            f"❌ <b>BOT CRASHED!</b>\n\n"
            f"📄 <code>{ef}</code>\n"
            f"🔢 Exit: {proc.returncode} | Attempt: {att}/3\n\n"
            f"📋 Error:\n<code>{err_display}</code>",
            reply_markup=m
        )

        db.update_bot(bid, status='crashed',
                      last_crash=datetime.now().isoformat(),
                      error_log=err[-500:])
        cleanup_script(sk)

        # Forward crash to error bot
        forward_error("BOT_CRASH", f"Bot #{bid} crashed", uid, err[-500:])

    except Exception as e:
        logger.error(f"Run error: {e}", exc_info=True)
        forward_crash("run_bot_script", e, uid)
        safe_send(cid, f"❌ Fatal error: {str(e)[:200]}")
        cleanup_script(sk)


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
                                cleanup_script(sk)
                                time.sleep(5)
                                threading.Thread(
                                    target=run_bot_script,
                                    args=(bid, uid, i.get('attempt', 1) + 1),
                                    daemon=True
                                ).start()
                                continue
                    cleanup_script(sk)
        except Exception as e:
            logger.error(f"Monitor: {e}")
            forward_error("MONITOR_THREAD", e)
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
        except Exception as e:
            forward_error("BACKUP_THREAD", e)


def thread_expiry():
    while True:
        try:
            time.sleep(3600)
            now = datetime.now().isoformat()
            expired = db.exe(
                "SELECT * FROM users WHERE subscription_end<=? AND is_lifetime=0 AND plan!='free'",
                (now,), fetch=True
            ) or []
            for u in expired:
                uid = u['user_id']
                db.rem_sub(uid)
                for b in db.get_bots(uid):
                    sk = f"{uid}_{b['bot_name']}"
                    if sk in bot_scripts:
                        kill_tree(bot_scripts[sk])
                        cleanup_script(sk)
                    db.update_bot(b['bot_id'], status='stopped')
                safe_send(uid,
                    f"⚠️ <b>Subscription Expired!</b>\n\n"
                    f"Your bots have been stopped.\n"
                    f"Renew your plan to continue.\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━",
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("💎 Renew Plan", callback_data="menu_sub"),
                        types.InlineKeyboardButton("🏠 Menu", callback_data="go_home")
                    )
                )
        except Exception as e:
            forward_error("EXPIRY_THREAD", e)


# ═══════════════════════════════════════════════════
#  /START COMMAND
# ═══════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    un = msg.from_user.username or ''
    fn = f"{msg.from_user.first_name or ''} {msg.from_user.last_name or ''}".strip()
    state.active_users.add(uid)

    try:
        joined, nj = check_joined(uid)
        if not joined:
            send_force_sub(msg.chat.id, nj)
            return

        ex = db.get_user(uid)
        if ex and ex['is_banned']:
            return safe_reply(msg, f"🚫 <b>You are banned!</b>\nReason: {ex.get('ban_reason', 'N/A')}\n\nContact {YOUR_USERNAME}")
        if state.bot_locked and not state.is_admin(uid):
            return safe_reply(msg, "🔒 <b>Bot is in maintenance mode.</b>\nPlease try again later.")

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
                    f"👤 <b>{fn}</b> joined via your link!\n"
                    f"💰 +{REF_COMMISSION} BDT wallet bonus!\n"
                    f"📅 +{REF_BONUS_DAYS} days premium!\n"
                    f"👥 Total Referrals: {rd['referral_count'] if rd else '?'}\n"
                    f"{BRAND_FOOTER}"
                )
            for aid in state.admin_ids:
                safe_send(aid, f"👤 <b>New User!</b>\n{fn} (<code>{uid}</code>)\nRef: {ref_by or 'Direct'}")
        else:
            db.update_user(uid, username=un, full_name=fn, last_active=datetime.now().isoformat())
            if not ex.get('referral_code') or len(ex.get('referral_code', '')) < 5:
                db.update_user(uid, referral_code=code)

        u = db.get_user(uid)
        pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free']) if u else PLAN_LIMITS['free']
        bc = db.bot_count(uid)
        mx = '♾️' if pl['max_bots'] == -1 else str(pl['max_bots'])
        role = '👑 Owner' if uid == OWNER_ID else '⭐ Admin' if state.is_admin(uid) else pl['name']

        welcome = (
            f"🌟 <b>APON HOSTING PANEL</b> {BRAND_VER}\n"
            f"<i>Premium Bot Hosting Platform</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 Welcome, <b>{fn}</b>!\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"📦 Plan: {role}\n"
            f"🤖 Bots: {bc}/{mx}\n"
            f"💰 Wallet: {u['wallet_balance'] if u else 0} BDT\n"
            f"👥 Referrals: {u['referral_count'] if u else 0}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>What you can do:</b>\n"
            f"  📤 Deploy Python &amp; Node.js bots\n"
            f"  🔍 Smart auto-detection\n"
            f"  🎁 Earn with referrals\n"
            f"  💳 Easy payments\n\n"
            f"👇 <b>Choose from the menu below:</b>"
        )
        safe_send(msg.chat.id, welcome, reply_markup=main_menu_kb(uid))

    except Exception as e:
        forward_crash("cmd_start", e, uid)
        safe_send(msg.chat.id, "❌ An error occurred. Please try again.")


# ═══════════════════════════════════════════════════
#  /HELP COMMAND
# ═══════════════════════════════════════════════════
@bot.message_handler(commands=['help'])
def cmd_help(msg):
    uid = msg.from_user.id
    try:
        help_text = (
            f"📚 <b>HELP CENTER</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Welcome to {BRAND}!\n"
            f"Select a topic below to learn more.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        safe_send(uid, help_text, reply_markup=help_menu_kb())
    except Exception as e:
        forward_crash("cmd_help", e, uid)


# ═══════════════════════════════════════════════════
#  OTHER COMMANDS
# ═══════════════════════════════════════════════════
@bot.message_handler(commands=['admin'])
def cmd_admin(msg):
    uid = msg.from_user.id
    if not state.is_admin(uid):
        return safe_reply(msg, "❌ Admin access only!")
    show_admin_panel(uid)


@bot.message_handler(commands=['id'])
def cmd_id(msg):
    uid = msg.from_user.id
    safe_send(msg.chat.id,
        f"🆔 <b>Your Info</b>\n\n"
        f"👤 ID: <code>{uid}</code>\n"
        f"📛 Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}\n"
        f"👤 Username: @{msg.from_user.username or 'N/A'}\n"
        f"{BRAND_FOOTER}",
        reply_markup=back_btn()
    )


@bot.message_handler(commands=['ping'])
def cmd_ping(msg):
    start = time.time()
    m = safe_reply(msg, "🏓 Pinging...")
    if m:
        latency = round((time.time() - start) * 1000, 2)
        rn = len([k for k in bot_scripts if is_running(k)])
        safe_edit(
            f"🏓 <b>Pong!</b>\n\n"
            f"⚡ Latency: {latency}ms\n"
            f"⏱️ Uptime: {get_uptime()}\n"
            f"🤖 Running: {rn} bots\n"
            f"{BRAND_FOOTER}",
            msg.chat.id, m.message_id, reply_markup=back_btn()
        )


@bot.message_handler(commands=['reply'])
def cmd_reply_ticket(msg):
    uid = msg.from_user.id
    if not state.is_admin(uid):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return safe_reply(msg, "Usage: /reply TICKET_ID MESSAGE")
    try:
        tid = int(parts[1])
        reply_text = parts[2]
        ticket = db.get_ticket(tid)
        if not ticket:
            return safe_reply(msg, f"❌ Ticket #{tid} not found!")
        db.reply_ticket(tid, reply_text)
        safe_reply(msg, f"✅ Replied to ticket #{tid}")
        safe_send(ticket['user_id'],
            f"📩 <b>Ticket #{tid} — Admin Reply</b>\n\n"
            f"💬 {reply_text}\n"
            f"{BRAND_FOOTER}"
        )
    except ValueError:
        safe_reply(msg, "❌ Invalid ticket ID!")


@bot.message_handler(commands=['subscribe'])
def cmd_sub_admin(msg):
    if not state.is_admin(msg.from_user.id):
        return
    p = msg.text.split()
    if len(p) < 3:
        return safe_reply(msg, "Usage: /subscribe UID DAYS")
    try:
        target_uid = int(p[1])
        days = int(p[2])
        db.set_sub(target_uid, 'pro' if days > 0 else 'lifetime', days)
        safe_reply(msg, f"✅ Subscription set for <code>{target_uid}</code> — {days}d")
    except:
        safe_reply(msg, "❌ Error! Check format.")


@bot.message_handler(commands=['ban'])
def cmd_ban(msg):
    if not state.is_admin(msg.from_user.id):
        return
    p = msg.text.split(maxsplit=2)
    if len(p) < 2:
        return safe_reply(msg, "Usage: /ban UID [REASON]")
    try:
        target = int(p[1])
        reason = p[2] if len(p) > 2 else "Banned by admin"
        db.ban(target, reason)
        safe_reply(msg, f"🚫 Banned <code>{target}</code>")
    except:
        safe_reply(msg, "❌ Error!")


@bot.message_handler(commands=['unban'])
def cmd_unban(msg):
    if not state.is_admin(msg.from_user.id):
        return
    try:
        target = int(msg.text.split()[1])
        db.unban(target)
        safe_reply(msg, f"✅ Unbanned <code>{target}</code>")
    except:
        safe_reply(msg, "❌ Error!")


@bot.message_handler(commands=['give'])
def cmd_give(msg):
    if not state.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 3:
        return safe_reply(msg, "Usage: /give UID AMOUNT")
    try:
        target = int(parts[1])
        amount = float(parts[2])
        u = db.get_user(target)
        if not u:
            return safe_reply(msg, f"❌ User {target} not found!")
        db.wallet_tx(target, amount, 'bonus', f"Admin bonus by {msg.from_user.id}")
        safe_reply(msg, f"✅ +{amount} BDT → <code>{target}</code>")
        safe_send(target, f"🎁 <b>Admin Bonus!</b>\n💰 +{amount} BDT added!\n{BRAND_FOOTER}")
    except:
        safe_reply(msg, "❌ Error!")


@bot.message_handler(commands=['broadcast', 'bc'])
def cmd_broadcast(msg):
    uid = msg.from_user.id
    if not state.is_admin(uid):
        return
    text = msg.text.split(maxsplit=1)
    if len(text) < 2:
        state.set_state(uid, {'action': 'broadcast'})
        return safe_reply(msg, "📢 Send broadcast message now:")
    do_broadcast_send(uid, text[1], msg.chat.id)


@bot.message_handler(commands=['userinfo'])
def cmd_userinfo(msg):
    uid = msg.from_user.id
    if not state.is_admin(uid):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return safe_reply(msg, "Usage: /userinfo USER_ID")
    try:
        target = int(parts[1])
        show_user_info(uid, target)
    except ValueError:
        safe_reply(msg, "❌ Invalid user ID!")


@bot.message_handler(commands=['addchannel'])
def cmd_add_channel(msg):
    uid = msg.from_user.id
    if not state.is_admin(uid):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        return safe_reply(msg, "Usage: /addchannel @username [Channel Name]")
    ch_username = parts[1].lstrip('@').lower()
    ch_name = parts[2] if len(parts) > 2 else ch_username
    try:
        chat_info = bot.get_chat(f"@{ch_username}")
        ch_name = chat_info.title or ch_name
    except:
        pass
    db.add_channel(ch_username, ch_name, uid)
    db.admin_log(uid, 'add_channel', details=f"@{ch_username}")
    safe_reply(msg, f"✅ Channel @{ch_username} added!\n⚠️ Make sure bot is admin!")


@bot.message_handler(commands=['removechannel', 'rmchannel'])
def cmd_remove_channel(msg):
    if not state.is_admin(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return safe_reply(msg, "Usage: /removechannel @username")
    db.remove_channel(parts[1].lstrip('@').lower())
    safe_reply(msg, "✅ Removed!")


@bot.message_handler(commands=['stopbot'])
def cmd_stopbot(msg):
    if not state.is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return safe_reply(msg, "Usage: /stopbot BOT_ID")
    try:
        bid = int(parts[1])
        bd = db.get_bot(bid)
        if not bd:
            return safe_reply(msg, "❌ Bot not found!")
        sk = f"{bd['user_id']}_{bd['bot_name']}"
        if sk in bot_scripts:
            kill_tree(bot_scripts[sk])
            cleanup_script(sk)
        db.update_bot(bid, status='stopped')
        safe_reply(msg, f"✅ Stopped bot #{bid}")
    except:
        safe_reply(msg, "❌ Error!")


@bot.message_handler(commands=['notify'])
def cmd_notify(msg):
    if not state.is_admin(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return safe_reply(msg, "Usage: /notify USER_ID MESSAGE")
    try:
        target = int(parts[1])
        text = parts[2]
        db.add_notif(target, "Admin Notice", text)
        safe_reply(msg, f"✅ Notification sent to <code>{target}</code>")
        safe_send(target, f"🔔 <b>Notification</b>\n\n{text}\n{BRAND_FOOTER}")
    except:
        safe_reply(msg, "❌ Error!")


@bot.message_handler(commands=['channels'])
def cmd_channels(msg):
    if not state.is_admin(msg.from_user.id):
        return
    channels = db.get_all_channels()
    t = f"📢 <b>Force Subscribe Channels</b>\nStatus: {'🟢 ON' if state.force_sub_enabled else '🔴 OFF'}\n\n"
    if channels:
        for ch in channels:
            st = "🟢" if ch['is_active'] else "🔴"
            t += f"  {st} @{ch['channel_username']} — {ch['channel_name']}\n"
    else:
        t += "No channels. Default: @developer_apon_07\n"
    safe_send(msg.from_user.id, t, reply_markup=back_btn("menu_admin", "🔙 Admin"))


# ═══════════════════════════════════════════════════
#  HELPER DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════
def show_admin_panel(uid):
    s = db.stats()
    rn = len([k for k in bot_scripts if is_running(k)])
    tickets = len(db.open_tickets())
    safe_send(uid,
        f"👑 <b>ADMIN PANEL</b>\n"
        f"{BRAND_TAG}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {s['users']} (+{s['today']} today)\n"
        f"🤖 Running Bots: {rn}\n"
        f"💎 Active Subs: {s['active_subs']}\n"
        f"🚫 Banned: {s['banned']}\n"
        f"💳 Pending Payments: {s['pending']}\n"
        f"🎫 Open Tickets: {tickets}\n"
        f"💰 Total Revenue: {s['revenue']} BDT\n\n"
        f"🔐 Force Sub: {'🟢 ON' if state.force_sub_enabled else '🔴 OFF'}\n"
        f"🔒 Bot Lock: {'🔒 LOCKED' if state.bot_locked else '🔓 OPEN'}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=admin_kb()
    )


def show_user_info(admin_uid, target_uid):
    u = db.get_user(target_uid)
    if not u:
        safe_send(admin_uid, f"❌ User <code>{target_uid}</code> not found!")
        return
    pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
    bc = db.bot_count(target_uid)
    bots_list = db.get_bots(target_uid)
    running = sum(1 for b in bots_list if bot_running(target_uid, b['bot_name']))
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🚫 Ban", callback_data=f"adm_ban_direct:{target_uid}"),
        types.InlineKeyboardButton("✅ Unban", callback_data=f"adm_unban_direct:{target_uid}")
    )
    m.add(types.InlineKeyboardButton("🔙 Admin", callback_data="menu_admin"))
    safe_send(admin_uid,
        f"👤 <b>User Info</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{target_uid}</code>\n"
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
        f"📅 Joined: {u['created_at'][:16] if u.get('created_at') else '?'}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=m
    )


def do_broadcast_send(admin_uid, text, reply_cid=None):
    users = db.get_all_users()
    sent = failed = 0
    cid = reply_cid or admin_uid
    prog = safe_send(cid, f"📢 Broadcasting to {len(users)} users...")
    for u in users:
        try:
            safe_send(u['user_id'], f"📢 <b>Announcement</b>\n\n{text}\n{BRAND_FOOTER}")
            sent += 1
        except:
            failed += 1
        if (sent + failed) % 50 == 0 and prog:
            safe_edit(
                f"📢 Progress: {sent + failed}/{len(users)}\n✅ {sent} | ❌ {failed}",
                cid, prog.message_id
            )
    if prog:
        safe_edit(
            f"📢 <b>Broadcast Complete!</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {len(users)}",
            cid, prog.message_id,
            reply_markup=back_btn("menu_admin", "🔙 Admin")
        )
    db.admin_log(admin_uid, 'broadcast', details=f"sent:{sent} failed:{failed}")


# ═══════════════════════════════════════════════════
#  TEXT HANDLER (Simplified — all via buttons)
# ═══════════════════════════════════════════════════
@bot.message_handler(content_types=['text'])
def handle_text(msg):
    uid = msg.from_user.id
    txt = msg.text.strip()
    state.active_users.add(uid)

    try:
        if not rate_check(uid):
            return

        joined, nj = check_joined(uid)
        if not joined:
            send_force_sub(msg.chat.id, nj)
            return

        u = db.get_user(uid)
        if u and u['is_banned']:
            return
        if state.bot_locked and not state.is_admin(uid):
            return safe_reply(msg, "🔒 <b>Maintenance mode.</b> Please wait.")

        # Handle payment state
        if state.get_pay_state(uid):
            return handle_pay_text(msg)

        # Handle other states
        user_state = state.get_state(uid)
        if user_state:
            return handle_user_state(msg)

        # Default: show main menu
        if not u:
            safe_send(uid, "Please press /start first!")
            return

        safe_send(uid,
            f"🏠 <b>Main Menu</b>\n\n"
            f"Use the buttons below to navigate.\n"
            f"Or type /help for assistance.\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            reply_markup=main_menu_kb(uid)
        )

    except Exception as e:
        forward_crash("handle_text", e, uid)


# ═══════════════════════════════════════════════════
#  STATE HANDLER (All admin/user input states)
# ═══════════════════════════════════════════════════
def handle_user_state(msg):
    uid = msg.from_user.id
    s = state.get_state(uid)
    if not s:
        return

    action = s.get('action')
    
    try:
        if action == 'broadcast':
            if not state.is_admin(uid):
                state.clear_state(uid)
                return
            do_broadcast_send(uid, msg.text, msg.chat.id)
            state.clear_state(uid)

        elif action == 'adm_addsub_uid':
            try:
                target = int(msg.text.strip())
                target_user = db.get_user(target)
                if not target_user:
                    safe_reply(msg, f"❌ User <code>{target}</code> not found!")
                    state.clear_state(uid)
                    return
                m = types.InlineKeyboardMarkup(row_width=2)
                for k, p in PLAN_LIMITS.items():
                    if k != 'free':
                        m.add(types.InlineKeyboardButton(
                            p['name'], callback_data=f"adm_setplan:{k}:{target}"
                        ))
                m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
                safe_reply(msg,
                    f"👤 User: <code>{target}</code> — {target_user['full_name']}\n"
                    f"Current: {PLAN_LIMITS.get(target_user['plan'], PLAN_LIMITS['free'])['name']}\n\n"
                    f"Select new plan:",
                    reply_markup=m
                )
                state.clear_state(uid)
            except ValueError:
                safe_reply(msg, "❌ Invalid user ID! Send a number.")
                state.clear_state(uid)

        elif action == 'adm_addsub_days':
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
                safe_reply(msg,
                    f"✅ <b>Subscription Added!</b>\n\n"
                    f"👤 User: <code>{target}</code>\n"
                    f"📦 Plan: {plan_name}\n"
                    f"📅 Duration: {'Lifetime' if days == 0 else f'{days} days'}",
                    reply_markup=back_btn("menu_admin", "🔙 Admin")
                )
                db.admin_log(uid, 'add_sub', target, f"{plan}/{days}d")
                safe_send(target,
                    f"🎉 <b>Plan Upgraded!</b>\n📦 {plan_name}\n"
                    f"📅 {'Lifetime' if days == 0 else f'{days} days'}\n{BRAND_FOOTER}")
            except ValueError:
                safe_reply(msg, "❌ Send a number! (0 = lifetime)")
            state.clear_state(uid)

        elif action == 'adm_remsub_uid':
            try:
                target = int(msg.text.strip())
                db.rem_sub(target)
                safe_reply(msg,
                    f"✅ Subscription removed: <code>{target}</code>",
                    reply_markup=back_btn("menu_admin", "🔙 Admin")
                )
                db.admin_log(uid, 'remove_sub', target)
                safe_send(target, "⚠️ Your subscription has been removed by admin.")
            except:
                safe_reply(msg, "❌ Invalid user ID!")
            state.clear_state(uid)

        elif action == 'adm_ban_uid':
            parts = msg.text.strip().split(maxsplit=1)
            try:
                target = int(parts[0])
                reason = parts[1] if len(parts) > 1 else "Banned by admin"
                db.ban(target, reason)
                db.admin_log(uid, 'ban', target, reason)
                # Stop all bots
                for b in db.get_bots(target):
                    sk = f"{target}_{b['bot_name']}"
                    if sk in bot_scripts:
                        kill_tree(bot_scripts[sk])
                        cleanup_script(sk)
                    db.update_bot(b['bot_id'], status='stopped')
                safe_reply(msg,
                    f"🚫 Banned <code>{target}</code>\nReason: {reason}",
                    reply_markup=back_btn("menu_admin", "🔙 Admin")
                )
                safe_send(target, f"🚫 <b>You have been banned!</b>\nReason: {reason}\n\nContact {YOUR_USERNAME}")
            except:
                safe_reply(msg, "❌ Format: USER_ID [REASON]")
            state.clear_state(uid)

        elif action == 'adm_unban_uid':
            try:
                target = int(msg.text.strip())
                db.unban(target)
                db.admin_log(uid, 'unban', target)
                safe_reply(msg,
                    f"✅ Unbanned <code>{target}</code>",
                    reply_markup=back_btn("menu_admin", "🔙 Admin")
                )
                safe_send(target, "✅ You have been unbanned! Welcome back.")
            except:
                safe_reply(msg, "❌ Invalid user ID!")
            state.clear_state(uid)

        elif action == 'adm_promo_create':
            parts = msg.text.strip().split()
            if len(parts) >= 3:
                try:
                    code = parts[0].upper()
                    discount = int(parts[1])
                    max_uses = int(parts[2])
                    db.add_promo(code, discount, max_uses, uid)
                    safe_reply(msg,
                        f"✅ <b>Promo Created!</b>\n\n"
                        f"🎟 Code: <code>{code}</code>\n"
                        f"💰 Discount: {discount}%\n"
                        f"🔢 Max Uses: {max_uses}",
                        reply_markup=back_btn("menu_admin", "🔙 Admin")
                    )
                    db.admin_log(uid, 'create_promo', details=f"{code}/{discount}%/{max_uses}")
                except:
                    safe_reply(msg, "❌ Error creating promo!")
            else:
                safe_reply(msg, "❌ Format: CODE DISCOUNT% MAX_USES\nEx: SAVE50 50 100")
            state.clear_state(uid)

        elif action == 'adm_give_balance':
            parts = msg.text.strip().split()
            if len(parts) >= 2:
                try:
                    target = int(parts[0])
                    amount = float(parts[1])
                    u_target = db.get_user(target)
                    if not u_target:
                        safe_reply(msg, f"❌ User {target} not found!")
                    else:
                        db.wallet_tx(target, amount, 'bonus', f"Admin bonus by {uid}")
                        safe_reply(msg,
                            f"✅ +{amount} BDT → <code>{target}</code>",
                            reply_markup=back_btn("menu_admin", "🔙 Admin")
                        )
                        safe_send(target, f"🎁 <b>Admin Bonus!</b>\n💰 +{amount} BDT\n{BRAND_FOOTER}")
                except:
                    safe_reply(msg, "❌ Error!")
            else:
                safe_reply(msg, "❌ Format: USER_ID AMOUNT")
            state.clear_state(uid)

        elif action == 'adm_userinfo_uid':
            try:
                target = int(msg.text.strip())
                show_user_info(uid, target)
            except ValueError:
                safe_reply(msg, "❌ Invalid user ID!")
            state.clear_state(uid)

        elif action == 'adm_notify_uid':
            try:
                parts = msg.text.strip().split(maxsplit=1)
                target = int(parts[0])
                text = parts[1] if len(parts) > 1 else "Notification from admin"
                db.add_notif(target, "Admin Notice", text)
                safe_reply(msg,
                    f"✅ Sent to <code>{target}</code>",
                    reply_markup=back_btn("menu_admin", "🔙 Admin")
                )
                safe_send(target, f"🔔 <b>Notification</b>\n\n{text}\n{BRAND_FOOTER}")
            except:
                safe_reply(msg, "❌ Format: USER_ID MESSAGE")
            state.clear_state(uid)

        elif action == 'ch_add':
            text = msg.text.strip()
            parts = text.split(maxsplit=1)
            ch_username = parts[0].lstrip('@').lower()
            ch_name = parts[1] if len(parts) > 1 else ch_username
            try:
                chat_info = bot.get_chat(f"@{ch_username}")
                ch_name = chat_info.title or ch_name
            except:
                pass
            db.add_channel(ch_username, ch_name, uid)
            db.admin_log(uid, 'add_channel', details=f"@{ch_username}")
            safe_reply(msg,
                f"✅ <b>Channel Added!</b>\n📢 @{ch_username}\n⚠️ Make sure bot is admin!",
                reply_markup=back_btn("adm_channels", "🔙 Channels")
            )
            state.clear_state(uid)

        elif action == 'ch_remove':
            text = msg.text.strip().lstrip('@').lower()
            db.remove_channel(text)
            db.admin_log(uid, 'remove_channel', details=f"@{text}")
            safe_reply(msg,
                f"✅ Removed @{text}",
                reply_markup=back_btn("adm_channels", "🔙 Channels")
            )
            state.clear_state(uid)

        elif action == 'ticket':
            text = msg.text.strip()
            if len(text) < 5:
                safe_reply(msg, "❌ Message too short! Min 5 chars.")
                state.clear_state(uid)
                return
            tid = db.add_ticket(uid, "Support Request", text)
            safe_reply(msg,
                f"✅ <b>Ticket #{tid} Created!</b>\n\n"
                f"📝 {text[:100]}...\n\n"
                f"Our team will respond soon.\n"
                f"📞 Direct: {YOUR_USERNAME}\n{BRAND_FOOTER}",
                reply_markup=back_btn()
            )
            u = db.get_user(uid)
            for aid in state.admin_ids:
                m = types.InlineKeyboardMarkup()
                m.add(types.InlineKeyboardButton(
                    f"💬 Reply #{tid}", callback_data=f"adm_ticket_reply:{tid}"
                ))
                safe_send(aid,
                    f"🎫 <b>New Ticket #{tid}</b>\n\n"
                    f"👤 {u['full_name'] if u else uid} (<code>{uid}</code>)\n"
                    f"📝 {text[:200]}",
                    reply_markup=m
                )
            state.clear_state(uid)

        elif action == 'ticket_reply':
            tid = s.get('ticket_id')
            text = msg.text.strip()
            if not text or not tid:
                state.clear_state(uid)
                return
            ticket = db.get_ticket(tid)
            if ticket:
                db.reply_ticket(tid, text)
                safe_reply(msg,
                    f"✅ Replied to ticket #{tid}",
                    reply_markup=back_btn("adm_tickets", "🔙 Tickets")
                )
                safe_send(ticket['user_id'],
                    f"📩 <b>Ticket #{tid} — Reply</b>\n\n💬 {text}\n{BRAND_FOOTER}")
            state.clear_state(uid)

        else:
            state.clear_state(uid)

    except Exception as e:
        forward_crash("handle_user_state", e, uid)
        state.clear_state(uid)


# ═══════════════════════════════════════════════════
#  PAYMENT TEXT HANDLER
# ═══════════════════════════════════════════════════
def handle_pay_text(msg):
    uid = msg.from_user.id
    s = state.get_pay_state(uid)
    if not s or s.get('step') != 'wait_trx':
        return

    try:
        trx = msg.text.strip() if msg.text else 'SCREENSHOT'
        if not trx or len(trx) < 3:
            return safe_reply(msg, "❌ Please send a valid Transaction ID!")

        pid = db.add_pay(uid, s['amount'], s['method'], trx, s['plan'], 30)
        state.clear_pay_state(uid)

        safe_send(uid,
            f"✅ <b>PAYMENT SUBMITTED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 Payment ID: #{pid}\n"
            f"💰 Amount: {s['amount']} BDT\n"
            f"💳 Method: {s['method']}\n"
            f"📦 Plan: {PLAN_LIMITS.get(s['plan'], {}).get('name', s['plan'])}\n"
            f"🔖 TRX: <code>{trx}</code>\n\n"
            f"⏳ Waiting for admin approval...\n"
            f"━━━━━━━━━━━━━━━━━━━━",
            reply_markup=back_btn()
        )

        u = db.get_user(uid)
        method_info = PAYMENT_METHODS.get(s['method'], {})
        for aid in state.admin_ids:
            safe_send(aid,
                f"💳 <b>NEW PAYMENT!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 {u['full_name'] if u else '?'} (<code>{uid}</code>)\n"
                f"📦 Plan: {s['plan']}\n"
                f"💰 Amount: {s['amount']} BDT\n"
                f"{method_info.get('icon', '💳')} {method_info.get('name', s['method'])}\n"
                f"🔖 TRX: <code>{trx}</code>\n"
                f"🆔 #{pid}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                reply_markup=pay_approve_kb(pid)
            )
    except Exception as e:
        forward_crash("handle_pay_text", e, uid)
        state.clear_pay_state(uid)


# ═══════════════════════════════════════════════════
#  DOCUMENT HANDLER
# ═══════════════════════════════════════════════════
@bot.message_handler(content_types=['document'])
def handle_doc(msg):
    uid = msg.from_user.id

    try:
        joined, nj = check_joined(uid)
        if not joined:
            send_force_sub(msg.chat.id, nj)
            return

        u = db.get_user(uid)
        if not u:
            return safe_reply(msg, "Please /start first!")
        if u['is_banned']:
            return

        pl = db.get_plan(uid)
        cur = db.bot_count(uid)
        mx = pl['max_bots']
        if mx != -1 and cur >= mx:
            return safe_reply(msg,
                f"❌ <b>Bot limit reached!</b> ({cur}/{mx})\nUpgrade your plan for more slots.",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("💎 Upgrade", callback_data="menu_sub")
                )
            )

        fn = msg.document.file_name
        fs = msg.document.file_size
        ext = fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''

        allowed = ['py', 'js', 'zip', 'json', 'txt', 'env', 'yml', 'yaml', 'cfg', 'ini', 'toml']
        if ext not in allowed:
            return safe_reply(msg, f"❌ Unsupported file: .{ext}\n\nSupported: {', '.join(allowed)}")

        if fs > 100 * 1024 * 1024:
            return safe_reply(msg, "❌ File too large! Max 100MB.")

        pm = safe_reply(msg, f"📤 Uploading <code>{fn[:25]}</code> ({fmt_size(fs)})...")

        fi = bot.get_file(msg.document.file_id)
        dl = bot.download_file(fi.file_path)

        uf = user_folder(uid)

        if ext == 'zip':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp:
                tmp.write(dl)
                tp = tmp.name

            try:
                with zipfile.ZipFile(tp, 'r') as z:
                    for n in z.namelist():
                        if n.startswith('/') or '..' in n:
                            if pm:
                                safe_edit("❌ Suspicious file paths in ZIP!", msg.chat.id, pm.message_id)
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
                    af = [
                        os.path.relpath(os.path.join(r, f), ed)
                        for r, d, fs_list in os.walk(ed)
                        for f in fs_list if f.endswith(('.py', '.js'))
                    ]
                    err_text = f"❌ <b>No entry file detected!</b>\n\n📁 Files in ZIP:\n"
                    for f in af[:15]:
                        err_text += f"  • <code>{f}</code>\n"
                    if not af:
                        err_text += "  (No .py or .js files)\n"
                    err_text += "\n💡 Make sure ZIP has main.py, app.py, or bot.py"
                    if pm:
                        safe_edit(err_text, msg.chat.id, pm.message_id, reply_markup=back_btn())
                    return

                bid = db.add_bot(uid, bn, ed, entry, ft, '', fs, '')

                mk = types.InlineKeyboardMarkup(row_width=2)
                mk.add(
                    types.InlineKeyboardButton("▶️ Start Now", callback_data=f"bot_start:{bid}"),
                    types.InlineKeyboardButton("🤖 My Bots", callback_data="menu_mybots")
                )
                mk.add(types.InlineKeyboardButton("🔍 Re-detect", callback_data=f"bot_redetect:{bid}"))

                if pm:
                    safe_edit(
                        f"✅ <b>ZIP DEPLOYED!</b>\n\n"
                        f"📦 <code>{bn[:20]}</code>\n"
                        f"🆔 Bot ID: #{bid}\n\n"
                        f"🔍 <b>Detection:</b>\n{report}",
                        msg.chat.id, pm.message_id, reply_markup=mk
                    )

            except zipfile.BadZipFile:
                if pm:
                    safe_edit("❌ Invalid or corrupted ZIP file!", msg.chat.id, pm.message_id)
                try:
                    os.unlink(tp)
                except:
                    pass

        elif ext in ['py', 'js']:
            file_path = os.path.join(uf, fn)
            with open(file_path, 'wb') as f:
                f.write(dl)

            bid = db.add_bot(uid, fn, uf, fn, ext, '', fs, 'exact')

            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(
                types.InlineKeyboardButton("▶️ Run Now", callback_data=f"bot_start:{bid}"),
                types.InlineKeyboardButton("🤖 My Bots", callback_data="menu_mybots")
            )

            if pm:
                safe_edit(
                    f"✅ <b>FILE UPLOADED!</b>\n\n"
                    f"📄 <code>{fn[:25]}</code>\n"
                    f"🆔 Bot ID: #{bid}\n"
                    f"🔤 {'🐍 Python' if ext == 'py' else '🟨 Node.js'}\n"
                    f"📊 Size: {fmt_size(fs)}",
                    msg.chat.id, pm.message_id, reply_markup=mk
                )

        else:
            file_path = os.path.join(uf, fn)
            with open(file_path, 'wb') as f:
                f.write(dl)
            if pm:
                safe_edit(
                    f"✅ Config file <code>{fn}</code> saved!",
                    msg.chat.id, pm.message_id,
                    reply_markup=back_btn()
                )

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        forward_crash("handle_doc", e, uid)
        safe_send(msg.chat.id, f"❌ Upload error: {str(e)[:100]}")


# ═══════════════════════════════════════════════════
#  MASTER CALLBACK HANDLER
# ═══════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid = call.from_user.id
    data = call.data
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    try:
        # ═══════════════════════════════════════
        #  NAVIGATION
        # ═══════════════════════════════════════
        if data == "go_home":
            safe_answer(call.id)
            u = db.get_user(uid)
            if not u:
                db.create_user(uid, call.from_user.username or '', 
                              f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip(),
                              gen_ref_code(uid))
            safe_edit(
                f"🏠 <b>Main Menu</b>\n\n"
                f"Welcome back! Choose an option below.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=main_menu_kb(uid)
            )

        elif data == "verify_join":
            joined, nj = check_joined(uid)
            if joined:
                safe_answer(call.id, "✅ Verified! Welcome!", show_alert=True)
                safe_delete(chat_id, msg_id)
                u = db.get_user(uid)
                fn = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
                if not u:
                    db.create_user(uid, call.from_user.username or '', fn, gen_ref_code(uid))
                safe_send(uid,
                    f"✅ <b>Verification Successful!</b>\n\n"
                    f"Welcome, <b>{fn}</b>!\n"
                    f"━━━━━━━━━━━━━━━━━━━━",
                    reply_markup=main_menu_kb(uid)
                )
            else:
                safe_answer(call.id, "❌ Join all channels first!", show_alert=True)

        # ═══════════════════════════════════════
        #  MAIN MENU ITEMS
        # ═══════════════════════════════════════
        elif data == "menu_mybots":
            safe_answer(call.id)
            bots_list = db.get_bots(uid)
            pl = db.get_plan(uid)
            mx = '♾️' if pl['max_bots'] == -1 else str(pl['max_bots'])

            if not bots_list:
                m = types.InlineKeyboardMarkup(row_width=2)
                m.add(types.InlineKeyboardButton("📤 Deploy Bot", callback_data="menu_deploy"))
                m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
                safe_edit(
                    f"📭 <b>No bots yet!</b>\n\n"
                    f"Deploy your first bot using 📤 Deploy\n"
                    f"📦 Available Slots: 0/{mx}\n"
                    f"━━━━━━━━━━━━━━━━━━━━",
                    chat_id, msg_id, reply_markup=m
                )
                return

            rn = sum(1 for b in bots_list if bot_running(uid, b['bot_name']))
            t = (
                f"🤖 <b>My Bots</b> ({len(bots_list)})\n"
                f"🟢 Running: {rn} | 🔴 Stopped: {len(bots_list) - rn}\n"
                f"📦 Limit: {mx}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            m = types.InlineKeyboardMarkup(row_width=1)
            for b in bots_list:
                r = bot_running(uid, b['bot_name'])
                ic = "🐍" if b['file_type'] == 'py' else "🟨"
                st_icon = "🟢" if r else "🔴"
                t += f"{st_icon} {ic} <code>{b['bot_name'][:20]}</code> — #{b['bot_id']}\n"
                m.add(types.InlineKeyboardButton(
                    f"{st_icon} {ic} {b['bot_name'][:15]} — #{b['bot_id']}",
                    callback_data=f"bot_detail:{b['bot_id']}"
                ))
            m.add(types.InlineKeyboardButton("📤 Deploy New Bot", callback_data="menu_deploy"))
            m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
            safe_edit(t, chat_id, msg_id, reply_markup=m)

        elif data == "menu_deploy":
            safe_answer(call.id)
            pl = db.get_plan(uid)
            cur = db.bot_count(uid)
            mx = pl['max_bots']
            if mx != -1 and cur >= mx:
                m = types.InlineKeyboardMarkup()
                m.add(types.InlineKeyboardButton("💎 Upgrade Plan", callback_data="menu_sub"))
                m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
                safe_edit(
                    f"⚠️ <b>Bot Limit Reached!</b>\n\n"
                    f"Current: {cur}/{mx}\nUpgrade your plan for more slots.",
                    chat_id, msg_id, reply_markup=m
                )
                return
            rem = '♾️' if mx == -1 else str(mx - cur)
            safe_edit(
                f"📤 <b>DEPLOY YOUR BOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📎 Send your file now!\n\n"
                f"<b>Supported:</b>\n"
                f"  🐍 Python (.py)\n"
                f"  🟨 Node.js (.js)\n"
                f"  📦 ZIP archive\n\n"
                f"<b>Smart Detection:</b>\n"
                f"  🔍 Auto-finds entry file\n"
                f"  📦 Auto-install requirements.txt\n"
                f"  📦 Auto-install package.json\n\n"
                f"📊 Slots remaining: <b>{rem}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id,
                reply_markup=back_btn()
            )

        elif data == "menu_sub":
            safe_answer(call.id)
            u = db.get_user(uid)
            pl = PLAN_LIMITS.get(u['plan'] if u else 'free', PLAN_LIMITS['free'])
            t = (
                f"💎 <b>SUBSCRIPTION</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 Current Plan: {pl['name']}\n"
                f"📅 Expires: {time_left(u['subscription_end'] if u else None)}\n"
                f"🤖 Slots: {'♾️' if pl['max_bots'] == -1 else pl['max_bots']}\n"
                f"💾 RAM: {pl['ram']}MB\n"
                f"🔄 Auto Restart: {'✅' if pl['auto_restart'] else '❌'}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Available Plans:</b>\n\n"
            )
            for k, p in PLAN_LIMITS.items():
                if k == 'free':
                    continue
                slots = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
                t += (
                    f"{p['name']}\n"
                    f"  🤖 {slots} bots | 💾 {p['ram']}MB\n"
                    f"  🔄 Auto-restart: {'✅' if p['auto_restart'] else '❌'}\n"
                    f"  💰 <b>{p['price']} BDT/month</b>\n\n"
                )
            safe_edit(t, chat_id, msg_id, reply_markup=plan_kb())

        elif data == "menu_wallet":
            safe_answer(call.id)
            u = db.get_user(uid)
            if not u:
                return
            h = db.wallet_hist(uid, 7)
            t = (
                f"💰 <b>WALLET</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💵 Balance: <b>{u['wallet_balance']} BDT</b>\n"
                f"💰 Total Earned: {u['referral_earnings']} BDT\n"
                f"💳 Total Spent: {u['total_spent']} BDT\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Recent Transactions:</b>\n"
            )
            for x in h:
                ic = "➕" if x['tx_type'] in ('credit', 'referral', 'bonus', 'refund') else "➖"
                t += f"  {ic} {x['amount']} BDT — {x['description'][:30]}\n"
            if not h:
                t += "  (No transactions yet)\n"
            t += "━━━━━━━━━━━━━━━━━━━━"
            safe_edit(t, chat_id, msg_id, reply_markup=back_btn())

        elif data == "menu_ref":
            safe_answer(call.id)
            u = db.get_user(uid)
            if not u:
                return
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
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔑 Code: <code>{rc}</code>\n"
                f"🔗 Link:\n<code>{lnk}</code>\n\n"
                f"👥 Referrals: {u['referral_count']}\n"
                f"{lvl_icons.get(u['referral_level'], '🥉')} Level: {u['referral_level'].title()}\n"
                f"💰 Earned: {u['referral_earnings']} BDT\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 <b>{REF_COMMISSION} BDT</b> + 📅 <b>{REF_BONUS_DAYS} days</b> per referral!\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(
                types.InlineKeyboardButton("📋 Copy Referral Link", callback_data=f"ref_copy:{rc}"),
                types.InlineKeyboardButton("📋 My Referrals", callback_data="ref_list"),
                types.InlineKeyboardButton("🏆 Leaderboard", callback_data="ref_board"),
                types.InlineKeyboardButton("📤 Share", switch_inline_query=f"🚀 Join {BRAND}! {lnk}"),
                types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
            )
            safe_edit(t, chat_id, msg_id, reply_markup=m)

        elif data == "menu_stats":
            safe_answer(call.id)
            s = db.stats()
            ss = sys_stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            safe_edit(
                f"📊 <b>STATISTICS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>System:</b>\n"
                f"  🖥️ CPU: {ss['cpu']}%\n"
                f"  🧠 RAM: {ss['mem']}% ({ss['mem_used']}/{ss['mem_total']})\n"
                f"  💾 Disk: {ss['disk']}% ({ss['disk_used']}/{ss['disk_total']})\n"
                f"  ⏱️ Uptime: {ss['up']}\n\n"
                f"<b>Platform:</b>\n"
                f"  🤖 Running Bots: {rn}\n"
                f"  👥 Total Users: {s['users']}\n"
                f"  📅 New Today: {s['today']}\n"
                f"  💎 Active Subs: {s['active_subs']}\n"
                f"  💰 Revenue: {s['revenue']} BDT\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_btn()
            )

        elif data == "menu_running":
            safe_answer(call.id)
            r_list = []
            for sk, i in bot_scripts.items():
                if is_running(sk) and (state.is_admin(uid) or i.get('user_id') == uid):
                    up = str(datetime.now() - i.get('start_time', datetime.now())).split('.')[0]
                    ram, cpu = bot_res(sk)
                    r_list.append((i, up, ram, cpu))
            
            if not r_list:
                safe_edit(
                    "🔴 <b>No bots running!</b>\n\nDeploy and start a bot first.\n━━━━━━━━━━━━━━━━━━━━",
                    chat_id, msg_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("📤 Deploy", callback_data="menu_deploy"),
                        types.InlineKeyboardButton("🏠 Menu", callback_data="go_home")
                    )
                )
                return

            t = f"🟢 <b>Running Bots ({len(r_list)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            m = types.InlineKeyboardMarkup(row_width=1)
            for i, up, ram, cpu in r_list:
                bid = i.get('bot_id', '?')
                t += (
                    f"📄 <code>{i.get('file_name', '?')[:20]}</code>\n"
                    f"  PID: {i['process'].pid} | ⏱️ {up}\n"
                    f"  💾 {ram}MB | ⚡ {cpu}%\n\n"
                )
                m.add(types.InlineKeyboardButton(
                    f"🛑 Stop #{bid}", callback_data=f"bot_stop:{bid}"
                ))
            m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
            safe_edit(t, chat_id, msg_id, reply_markup=m)

        elif data == "menu_speed":
            safe_answer(call.id)
            ss = sys_stats()
            safe_edit(
                f"⚡ <b>Speed Test</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🖥️ CPU: {ss['cpu']}%\n"
                f"🧠 RAM: {ss['mem']}% ({ss['mem_used']}/{ss['mem_total']})\n"
                f"💾 Disk: {ss['disk']}%\n"
                f"⏱️ Uptime: {ss['up']}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_btn()
            )

        elif data == "menu_notif":
            safe_answer(call.id)
            notifs = db.get_notifs(uid, 10)
            t = f"🔔 <b>Notifications</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for n in notifs:
                ic = "🔴" if not n['is_read'] else "⚪"
                t += f"{ic} <b>{n['title']}</b>\n  {n['message'][:60]}\n  📅 {n['created_at'][:16]}\n\n"
            if not notifs:
                t += "📭 No notifications yet!\n"
            db.mark_read(uid)
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=back_btn())

        elif data == "menu_support":
            safe_answer(call.id)
            state.set_state(uid, {'action': 'ticket'})
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(
                types.InlineKeyboardButton("📞 Direct Contact", url=f"https://t.me/developer_apon"),
                types.InlineKeyboardButton("❌ Cancel", callback_data="go_home")
            )
            safe_edit(
                f"🎫 <b>CREATE SUPPORT TICKET</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send your issue/question as a message.\n"
                f"Our team will respond ASAP!\n\n"
                f"📞 Or contact directly: {YOUR_USERNAME}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "menu_settings":
            safe_answer(call.id)
            u = db.get_user(uid)
            if not u:
                return
            pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("🇺🇸 English", callback_data="set_lang:en"),
                types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_lang:bn")
            )
            m.add(types.InlineKeyboardButton("📊 My Profile", callback_data="set_profile"))
            m.add(types.InlineKeyboardButton("💳 Payment History", callback_data="set_pay_history"))
            m.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home"))
            safe_edit(
                f"⚙️ <b>Settings</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 {u['full_name']}\n"
                f"🆔 <code>{uid}</code>\n"
                f"📅 Joined: {u['created_at'][:10] if u.get('created_at') else '?'}\n"
                f"📦 Plan: {pl['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        # ═══════════════════════════════════════
        #  HELP MENU — ALL BUTTONS WORKING
        # ═══════════════════════════════════════
        elif data == "menu_help":
            safe_answer(call.id)
            safe_edit(
                f"📚 <b>HELP CENTER</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Welcome to {BRAND}!\n"
                f"Select a topic below to learn more.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=help_menu_kb()
            )

        elif data == "help_deploy":
            safe_answer(call.id)
            safe_edit(
                f"📤 <b>HOW TO DEPLOY</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Step 1:</b> Prepare your bot file\n"
                f"  • Single .py or .js file\n"
                f"  • Or ZIP with all project files\n\n"
                f"<b>Step 2:</b> Send the file to this bot\n"
                f"  • Just drag &amp; drop or attach\n\n"
                f"<b>Step 3:</b> Auto-detection\n"
                f"  • Bot auto-finds entry file\n"
                f"  • Auto-installs dependencies\n\n"
                f"<b>Step 4:</b> Press ▶️ Start\n"
                f"  • Bot starts running instantly!\n\n"
                f"<b>💡 Tips:</b>\n"
                f"  • Name entry file main.py or app.py\n"
                f"  • Include requirements.txt\n"
                f"  • Use environment variables for tokens\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_bots":
            safe_answer(call.id)
            safe_edit(
                f"🤖 <b>MANAGING BOTS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>▶️ Start:</b> Run your bot\n"
                f"<b>🛑 Stop:</b> Stop running bot\n"
                f"<b>🔄 Restart:</b> Stop &amp; start again\n"
                f"<b>📋 Logs:</b> View bot output/errors\n"
                f"<b>📊 Resources:</b> RAM &amp; CPU usage\n"
                f"<b>🗑 Delete:</b> Remove bot permanently\n"
                f"<b>📥 Download:</b> Get your file back\n"
                f"<b>🔍 Re-detect:</b> Re-scan entry file\n\n"
                f"<b>Auto Features:</b>\n"
                f"  🔄 Auto-restart on crash (paid plans)\n"
                f"  📦 Auto-install missing modules\n"
                f"  🔍 Smart entry file detection\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_plans":
            safe_answer(call.id)
            t = f"💎 <b>PLANS &amp; PRICING</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for k, p in PLAN_LIMITS.items():
                slots = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
                ar = '✅' if p['auto_restart'] else '❌'
                price = 'FREE' if p['price'] == 0 else f"{p['price']} BDT/mo"
                t += (
                    f"{p['name']}\n"
                    f"  🤖 {slots} bots | 💾 {p['ram']}MB | 🔄 {ar}\n"
                    f"  💰 {price}\n\n"
                )
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(types.InlineKeyboardButton("💳 Buy Plan", callback_data="menu_sub"))
            m.add(
                types.InlineKeyboardButton("📚 Back to Help", callback_data="menu_help"),
                types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
            )
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=m)

        elif data == "help_payment":
            safe_answer(call.id)
            t = f"💳 <b>PAYMENT GUIDE</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for k, v in PAYMENT_METHODS.items():
                t += f"  {v['icon']} <b>{v['name']}</b>\n    📱 {v['number']}\n    📝 {v['type']}\n\n"
            t += (
                f"<b>Steps:</b>\n"
                f"  1. Select plan\n"
                f"  2. Choose payment method\n"
                f"  3. Send money to the number\n"
                f"  4. Send Transaction ID\n"
                f"  5. Wait for admin approval\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            safe_edit(t, chat_id, msg_id, reply_markup=back_help_btn())

        elif data == "help_referral":
            safe_answer(call.id)
            safe_edit(
                f"🎁 <b>REFERRAL SYSTEM</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>How it works:</b>\n"
                f"  1. Share your referral link\n"
                f"  2. Friend joins using your link\n"
                f"  3. You get <b>{REF_COMMISSION} BDT</b> wallet bonus\n"
                f"  4. You get <b>{REF_BONUS_DAYS} days</b> premium\n\n"
                f"<b>Levels:</b>\n"
                f"  🥉 Bronze: 0-9 referrals\n"
                f"  🥈 Silver: 10-24 referrals\n"
                f"  🥇 Gold: 25-49 referrals\n"
                f"  💠 Platinum: 50-99 referrals\n"
                f"  💎 Diamond: 100+ referrals\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_wallet":
            safe_answer(call.id)
            safe_edit(
                f"💰 <b>WALLET GUIDE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Earn Balance:</b>\n"
                f"  🎁 Referral bonuses\n"
                f"  🎟 Promo codes\n"
                f"  💰 Admin bonuses\n\n"
                f"<b>Spend Balance:</b>\n"
                f"  💎 Buy subscriptions directly\n"
                f"  (Select 'Pay from Wallet' at checkout)\n\n"
                f"All transactions are logged.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_detect":
            safe_answer(call.id)
            safe_edit(
                f"🔍 <b>AUTO DETECTION</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>How it works:</b>\n"
                f"Bot scans your files to find the entry point.\n\n"
                f"<b>Detection Priority:</b>\n"
                f"  1. main.py / app.py / bot.py\n"
                f"  2. package.json (main field)\n"
                f"  3. Procfile\n"
                f"  4. Code analysis (imports)\n\n"
                f"<b>Confidence Levels:</b>\n"
                f"  🎯 Exact — single file upload\n"
                f"  ✅ High — standard naming\n"
                f"  🟡 Medium — code analysis\n"
                f"  ⚠️ Low — fallback guess\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_files":
            safe_answer(call.id)
            safe_edit(
                f"📦 <b>SUPPORTED FILES</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Scripts:</b>\n"
                f"  🐍 .py — Python scripts\n"
                f"  🟨 .js — Node.js scripts\n\n"
                f"<b>Archives:</b>\n"
                f"  📦 .zip — ZIP archives\n\n"
                f"<b>Config Files:</b>\n"
                f"  📄 .json .txt .env\n"
                f"  📄 .yml .yaml .cfg .ini .toml\n\n"
                f"<b>Max Size:</b> 100MB\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_faq":
            safe_answer(call.id)
            safe_edit(
                f"❓ <b>FAQ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Q: Is it free?</b>\n"
                f"A: Yes! Free plan = 1 bot.\n\n"
                f"<b>Q: Will my bot run 24/7?</b>\n"
                f"A: Yes, with paid plans + auto-restart.\n\n"
                f"<b>Q: What languages supported?</b>\n"
                f"A: Python and Node.js.\n\n"
                f"<b>Q: How to use environment variables?</b>\n"
                f"A: Upload .env file or set BOT_TOKEN.\n\n"
                f"<b>Q: My bot crashed, what to do?</b>\n"
                f"A: Check logs, fix errors, restart.\n\n"
                f"<b>Q: Can I upload ZIP?</b>\n"
                f"A: Yes! Full project support.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_trouble":
            safe_answer(call.id)
            safe_edit(
                f"🛠 <b>TROUBLESHOOTING</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Bot won't start:</b>\n"
                f"  • Check entry file is correct\n"
                f"  • Use Re-detect button\n"
                f"  • Check logs for errors\n\n"
                f"<b>Module not found:</b>\n"
                f"  • Auto-install handles most cases\n"
                f"  • Include requirements.txt\n\n"
                f"<b>Bot crashes immediately:</b>\n"
                f"  • Check for syntax errors\n"
                f"  • Ensure token is correct\n"
                f"  • Check logs for details\n\n"
                f"<b>ZIP not working:</b>\n"
                f"  • Don't use nested folders\n"
                f"  • Place main.py at root\n"
                f"  • Include all dependencies\n\n"
                f"<b>Still stuck?</b>\n"
                f"  Create a support ticket!\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_help_btn()
            )

        elif data == "help_commands":
            safe_answer(call.id)
            t = (
                f"📋 <b>ALL COMMANDS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>User Commands:</b>\n"
                f"  /start — Start / Main Menu\n"
                f"  /help — Help Center\n"
                f"  /id — Your info\n"
                f"  /ping — Check bot status\n\n"
                f"<b>Admin Commands:</b>\n"
                f"  /admin — Admin panel\n"
                f"  /ban UID [reason] — Ban user\n"
                f"  /unban UID — Unban user\n"
                f"  /subscribe UID DAYS — Add sub\n"
                f"  /give UID AMOUNT — Give balance\n"
                f"  /broadcast MSG — Broadcast\n"
                f"  /userinfo UID — User details\n"
                f"  /stopbot BID — Stop a bot\n"
                f"  /notify UID MSG — Send notif\n"
                f"  /reply TID MSG — Reply ticket\n"
                f"  /addchannel @ch — Add force sub\n"
                f"  /removechannel @ch — Remove\n"
                f"  /channels — List channels\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            safe_edit(t, chat_id, msg_id, reply_markup=back_help_btn())

        elif data == "help_contact":
            safe_answer(call.id)
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(
                types.InlineKeyboardButton("📞 Contact Developer", url="https://t.me/developer_apon"),
                types.InlineKeyboardButton("📢 Updates Channel", url=UPDATE_CHANNEL),
                types.InlineKeyboardButton("🎫 Create Ticket", callback_data="menu_support")
            )
            m.add(
                types.InlineKeyboardButton("📚 Back to Help", callback_data="menu_help"),
                types.InlineKeyboardButton("🏠 Main Menu", callback_data="go_home")
            )
            safe_edit(
                f"📞 <b>CONTACT &amp; SUPPORT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👨‍💻 Developer: {YOUR_USERNAME}\n"
                f"📢 Channel: {UPDATE_CHANNEL}\n\n"
                f"🎫 Or create a support ticket below.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        # ═══════════════════════════════════════
        #  BOT OPERATIONS
        # ═══════════════════════════════════════
        elif data.startswith("bot_detail:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Bot not found!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            rn = is_running(sk)
            ram, cpu = bot_res(sk) if rn else (0, 0)
            uptime_str = "—"
            if rn and sk in bot_scripts:
                st = bot_scripts[sk].get('start_time')
                if st:
                    uptime_str = str(datetime.now() - st).split('.')[0]
            icon = "🐍" if bd['file_type'] == 'py' else "🟨"
            status_text = "🟢 Running" if rn else "🔴 Stopped"
            t = (
                f"{icon} <b>{bd['bot_name'][:22]}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 Bot ID: #{bid}\n"
                f"📄 Entry: <code>{bd['entry_file']}</code>\n"
                f"🔤 Type: {bd['file_type'].upper()}\n"
                f"📊 Status: {status_text}\n"
                f"💾 RAM: {ram}MB | ⚡ CPU: {cpu}%\n"
                f"⏱️ Uptime: {uptime_str}\n"
                f"🔄 Restarts: {bd['total_restarts']}\n"
                f"📅 Created: {bd['created_at'][:10] if bd.get('created_at') else '?'}\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            safe_edit(t, chat_id, msg_id, reply_markup=bot_action_kb(bid, rn))
            safe_answer(call.id)

        elif data.startswith("bot_start:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!", show_alert=True)
            if not db.is_active(bd['user_id']):
                return safe_answer(call.id, "⚠️ Subscription expired!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if is_running(sk):
                return safe_answer(call.id, "⚠️ Already running!", show_alert=True)
            safe_answer(call.id, "🚀 Starting...")
            threading.Thread(target=run_bot_script, args=(bid, chat_id), daemon=True).start()

        elif data.startswith("bot_stop:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if sk in bot_scripts:
                kill_tree(bot_scripts[sk])
                cleanup_script(sk)
            db.update_bot(bid, status='stopped', last_stopped=datetime.now().isoformat())
            safe_answer(call.id, "✅ Stopped!")
            # Refresh detail view
            call.data = f"bot_detail:{bid}"
            handle_callback(call)

        elif data.startswith("bot_restart:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            if sk in bot_scripts:
                kill_tree(bot_scripts[sk])
                cleanup_script(sk)
            db.update_bot(bid, total_restarts=bd['total_restarts'] + 1)
            time.sleep(2)
            safe_answer(call.id, "🔄 Restarting...")
            threading.Thread(target=run_bot_script, args=(bid, chat_id), daemon=True).start()

        elif data.startswith("bot_logs:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌ Not found!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            lp = os.path.join(LOGS_DIR, f"{sk}.log")
            logs = "📭 No logs available."
            if os.path.exists(lp):
                try:
                    with open(lp, 'r', encoding='utf-8', errors='ignore') as f:
                        logs = f.read()[-1500:] or "📭 Log file is empty."
                except:
                    logs = "❌ Error reading log file."
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("🔄 Refresh", callback_data=f"bot_logs:{bid}"),
                types.InlineKeyboardButton("🗑 Clear Logs", callback_data=f"bot_clearlogs:{bid}")
            )
            m.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"bot_detail:{bid}"))
            safe_edit(
                f"📋 <b>Logs — Bot #{bid}</b>\n\n<code>{logs}</code>"[:4000],
                chat_id, msg_id, reply_markup=m
            )
            safe_answer(call.id)

        elif data.startswith("bot_clearlogs:"):
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
            safe_answer(call.id, "🗑 Logs cleared!")
            call.data = f"bot_logs:{bid}"
            handle_callback(call)

        elif data.startswith("bot_res:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌!", show_alert=True)
            sk = f"{bd['user_id']}_{bd['bot_name']}"
            ram, cpu = bot_res(sk)
            uptime_str = "—"
            if sk in bot_scripts:
                st = bot_scripts[sk].get('start_time')
                if st:
                    uptime_str = str(datetime.now() - st).split('.')[0]
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("🔄 Refresh", callback_data=f"bot_res:{bid}"),
                types.InlineKeyboardButton("🔙 Back", callback_data=f"bot_detail:{bid}")
            )
            safe_edit(
                f"📊 <b>Resources — Bot #{bid}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💾 RAM: {ram}MB\n"
                f"⚡ CPU: {cpu}%\n"
                f"⏱️ Uptime: {uptime_str}\n"
                f"🔄 Total Restarts: {bd['total_restarts']}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )
            safe_answer(call.id)

        elif data.startswith("bot_redetect:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌!", show_alert=True)
            wd = bd['file_path'] if os.path.isdir(bd['file_path']) else user_folder(bd['user_id'])
            entry, ft, rp = det.report(wd)
            if entry:
                db.update_bot(bid, entry_file=entry, file_type=ft)
                m = types.InlineKeyboardMarkup(row_width=2)
                m.add(
                    types.InlineKeyboardButton("▶️ Start", callback_data=f"bot_start:{bid}"),
                    types.InlineKeyboardButton("🔙 Back", callback_data=f"bot_detail:{bid}")
                )
                safe_edit(
                    f"🔍 <b>Re-Detection Complete</b>\n\n{rp}\n\n✅ Entry file updated!",
                    chat_id, msg_id, reply_markup=m
                )
            else:
                af = [
                    os.path.relpath(os.path.join(r, f), wd)
                    for r, d, fs in os.walk(wd) for f in fs if f.endswith(('.py', '.js'))
                ]
                m = types.InlineKeyboardMarkup(row_width=1)
                for f in af[:10]:
                    ftype = 'js' if f.endswith('.js') else 'py'
                    m.add(types.InlineKeyboardButton(
                        f"📄 {f}", callback_data=f"bot_setentry:{bid}:{f}:{ftype}"
                    ))
                m.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"bot_detail:{bid}"))
                t = "🔍 ❌ <b>Auto-detect failed!</b>\n\nSelect entry file manually:\n"
                for f in af[:10]:
                    t += f"  • <code>{f}</code>\n"
                if not af:
                    t += "  (No .py or .js files found)\n"
                safe_edit(t, chat_id, msg_id, reply_markup=m)
            safe_answer(call.id)

        elif data.startswith("bot_setentry:"):
            parts = data.split(":")
            bid = int(parts[1])
            entry = parts[2]
            ft = parts[3]
            db.update_bot(bid, entry_file=entry, file_type=ft)
            safe_answer(call.id, f"✅ Entry set: {entry}")
            call.data = f"bot_detail:{bid}"
            handle_callback(call)

        elif data.startswith("bot_del:"):
            bid = int(data.split(":")[1])
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(
                types.InlineKeyboardButton("✅ Yes, Delete", callback_data=f"bot_confirm_del:{bid}"),
                types.InlineKeyboardButton("❌ Cancel", callback_data=f"bot_detail:{bid}")
            )
            safe_edit(
                f"🗑 <b>Delete Bot #{bid}?</b>\n\n"
                f"⚠️ This cannot be undone!\n"
                f"All files will be permanently removed.",
                chat_id, msg_id, reply_markup=m
            )
            safe_answer(call.id)

        elif data.startswith("bot_confirm_del:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if bd:
                sk = f"{bd['user_id']}_{bd['bot_name']}"
                if sk in bot_scripts:
                    kill_tree(bot_scripts[sk])
                    cleanup_script(sk)
                if os.path.isdir(bd['file_path']):
                    shutil.rmtree(bd['file_path'], ignore_errors=True)
                else:
                    fp = os.path.join(user_folder(bd['user_id']), bd['bot_name'])
                    try:
                        os.remove(fp)
                    except:
                        pass
                db.del_bot(bid)
            safe_answer(call.id, "✅ Bot deleted!")
            call.data = "menu_mybots"
            handle_callback(call)

        elif data.startswith("bot_dl:"):
            bid = int(data.split(":")[1])
            bd = db.get_bot(bid)
            if not bd:
                return safe_answer(call.id, "❌!", show_alert=True)
            fp = os.path.join(
                bd['file_path'], bd['entry_file']
            ) if os.path.isdir(bd['file_path']) else os.path.join(
                user_folder(bd['user_id']), bd['bot_name']
            )
            if os.path.exists(fp):
                try:
                    with open(fp, 'rb') as f:
                        bot.send_document(uid, f, caption=f"📄 {bd['bot_name']}")
                except:
                    safe_send(uid, "❌ Could not send file.")
            else:
                safe_send(uid, "❌ File not found on server.")
            safe_answer(call.id, "📥 Sending...")

        # ═══════════════════════════════════════
        #  REFERRAL CALLBACKS
        # ═══════════════════════════════════════
        elif data.startswith("ref_copy:"):
            rc = data.split(":", 1)[1]
            lnk = f"https://t.me/{BOT_USERNAME}?start={rc}"
            safe_answer(call.id)
            safe_send(uid, f"📋 <b>Your Referral Link:</b>\n\n<code>{lnk}</code>\n\n👆 Tap to copy!")

        elif data == "ref_list":
            refs = db.user_refs(uid)
            t = f"📋 <b>Your Referrals ({len(refs)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for r in refs[:20]:
                ru = db.get_user(r['referred_id'])
                name = ru['full_name'] if ru else str(r['referred_id'])
                t += f"  👤 {name} — +{r['commission']} BDT\n    📅 {r['created_at'][:10]}\n\n"
            if not refs:
                t += "No referrals yet! Share your link.\n"
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=back_btn("menu_ref", "🔙 Referral"))
            safe_answer(call.id)

        elif data == "ref_board":
            lb = db.ref_board(10)
            t = f"🏆 <b>Referral Leaderboard</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            medals = ['🥇', '🥈', '🥉']
            for i, l in enumerate(lb):
                icon = medals[i] if i < 3 else f"  #{i + 1}"
                t += f"{icon} {l['full_name'] or '?'} — {l['referral_count']} refs ({l['referral_earnings']} BDT)\n"
            if not lb:
                t += "No referrals yet!\n"
            safe_edit(t + "\n━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=back_btn("menu_ref", "🔙 Referral"))
            safe_answer(call.id)

        # ═══════════════════════════════════════
        #  PLAN & PAYMENT
        # ═══════════════════════════════════════
        elif data.startswith("plan_select:"):
            pk = data.split(":")[1]
            p = PLAN_LIMITS.get(pk)
            if not p:
                return safe_answer(call.id, "❌ Plan not found!", show_alert=True)
            slots = '♾️' if p['max_bots'] == -1 else str(p['max_bots'])
            safe_edit(
                f"{p['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🤖 Bot Slots: {slots}\n"
                f"💾 RAM: {p['ram']}MB\n"
                f"🔄 Auto Restart: {'✅' if p['auto_restart'] else '❌'}\n"
                f"💰 Price: <b>{p['price']} BDT/month</b>\n\n"
                f"Select payment method:\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=pay_method_kb(pk)
            )
            safe_answer(call.id)

        elif data.startswith("pay_method:"):
            parts = data.split(":")
            pk = parts[1]
            mk = parts[2]
            p = PLAN_LIMITS.get(pk)
            pm = PAYMENT_METHODS.get(mk)
            if not p or not pm:
                return safe_answer(call.id, "❌ Error!", show_alert=True)
            state.set_pay_state(uid, {
                'step': 'wait_trx', 'plan': pk, 'method': mk, 'amount': p['price']
            })
            safe_edit(
                f"{pm['icon']} <b>{pm['name']} Payment</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 Send to: <code>{pm['number']}</code>\n"
                f"📝 Type: {pm['type']}\n"
                f"💰 Amount: <b>{p['price']} BDT</b>\n"
                f"📦 Plan: {p['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📤 <b>Now send the Transaction ID below:</b>",
                chat_id, msg_id
            )
            safe_answer(call.id)

        elif data.startswith("pay_wallet:"):
            pk = data.split(":")[1]
            u = db.get_user(uid)
            p = PLAN_LIMITS.get(pk)
            if not u or not p:
                return safe_answer(call.id, "❌ Error!", show_alert=True)
            if u['wallet_balance'] < p['price']:
                return safe_answer(call.id,
                    f"❌ Insufficient balance!\nNeed: {p['price']} BDT | Have: {u['wallet_balance']} BDT",
                    show_alert=True
                )
            db.wallet_tx(uid, p['price'], 'purchase', f"Plan: {pk}")
            if pk == 'lifetime':
                db.set_sub(uid, 'lifetime')
            else:
                db.set_sub(uid, pk, 30)
            safe_answer(call.id, "✅ Plan activated!")
            safe_edit(
                f"✅ <b>Plan Activated!</b>\n\n"
                f"📦 {p['name']}\n"
                f"💰 Paid: {p['price']} BDT from wallet\n"
                f"{BRAND_FOOTER}",
                chat_id, msg_id, reply_markup=back_btn()
            )

        elif data.startswith("pay_approve:"):
            if not state.is_admin(uid):
                return safe_answer(call.id, "❌ Admin only!", show_alert=True)
            pid = int(data.split(":")[1])
            p = db.approve_pay(pid, uid)
            if p:
                safe_answer(call.id, "✅ Approved!")
                safe_edit(
                    (call.message.text or 'Payment') + "\n\n✅ <b>APPROVED</b>",
                    chat_id, msg_id
                )
                plan_name = PLAN_LIMITS.get(p['plan'], {}).get('name', p['plan'])
                safe_send(p['user_id'],
                    f"🎉 <b>Payment Approved!</b>\n\n"
                    f"📦 Plan: {plan_name}\n"
                    f"📅 Duration: {p['duration_days']} days\n"
                    f"{BRAND_FOOTER}",
                    reply_markup=back_btn()
                )
            else:
                safe_answer(call.id, "❌ Payment not found!", show_alert=True)

        elif data.startswith("pay_reject:"):
            if not state.is_admin(uid):
                return safe_answer(call.id, "❌ Admin only!", show_alert=True)
            pid = int(data.split(":")[1])
            pay = db.get_pay(pid)
            db.reject_pay(pid, uid)
            safe_answer(call.id, "❌ Rejected!")
            safe_edit(
                (call.message.text or 'Payment') + "\n\n❌ <b>REJECTED</b>",
                chat_id, msg_id
            )
            if pay:
                safe_send(pay['user_id'],
                    f"❌ <b>Payment Rejected</b>\n\n"
                    f"Payment #{pid} was not approved.\n"
                    f"Contact {YOUR_USERNAME} for help.\n"
                    f"{BRAND_FOOTER}"
                )

        # ═══════════════════════════════════════
        #  SETTINGS CALLBACKS
        # ═══════════════════════════════════════
        elif data.startswith("set_lang:"):
            lang = data.split(":")[1]
            db.update_user(uid, language=lang)
            safe_answer(call.id, "✅ Language updated!")

        elif data == "set_profile":
            safe_answer(call.id)
            u = db.get_user(uid)
            if not u:
                return
            pl = PLAN_LIMITS.get(u['plan'], PLAN_LIMITS['free'])
            bc = db.bot_count(uid)
            lvl_icons = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💠', 'diamond': '💎'}
            safe_edit(
                f"👤 <b>MY PROFILE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📛 {u['full_name']}\n"
                f"🆔 <code>{uid}</code>\n"
                f"👤 @{u['username'] or 'N/A'}\n\n"
                f"📦 Plan: {pl['name']}\n"
                f"📅 Expires: {time_left(u['subscription_end'])}\n"
                f"🤖 Bots: {bc}\n"
                f"💰 Wallet: {u['wallet_balance']} BDT\n"
                f"💳 Spent: {u['total_spent']} BDT\n\n"
                f"👥 Referrals: {u['referral_count']}\n"
                f"{lvl_icons.get(u['referral_level'], '🥉')} Level: {u['referral_level'].title()}\n"
                f"💰 Ref Earnings: {u['referral_earnings']} BDT\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id,
                reply_markup=back_btn("menu_settings", "🔙 Settings")
            )

        elif data == "set_pay_history":
            safe_answer(call.id)
            pays = db.user_payments(uid, 10)
            t = "💳 <b>Payment History</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for p in pays:
                st_icon = "✅" if p['status'] == 'approved' else "❌" if p['status'] == 'rejected' else "⏳"
                t += f"  {st_icon} #{p['payment_id']} — {p['amount']} BDT — {p['method']} — {p['status']}\n"
            if not pays:
                t += "  No payments yet.\n"
            safe_edit(
                t + "\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id,
                reply_markup=back_btn("menu_settings", "🔙 Settings")
            )

        # ═══════════════════════════════════════
        #  ADMIN PANEL CALLBACKS
        # ═══════════════════════════════════════
        elif data == "menu_admin":
            if not state.is_admin(uid):
                return safe_answer(call.id, "❌ Admin only!", show_alert=True)
            safe_answer(call.id)
            s = db.stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            tickets = len(db.open_tickets())
            safe_edit(
                f"👑 <b>ADMIN PANEL</b>\n"
                f"{BRAND_TAG}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 Total Users: {s['users']} (+{s['today']} today)\n"
                f"🤖 Running Bots: {rn}\n"
                f"💎 Active Subs: {s['active_subs']}\n"
                f"🚫 Banned: {s['banned']}\n"
                f"💳 Pending: {s['pending']}\n"
                f"🎫 Tickets: {tickets}\n"
                f"💰 Revenue: {s['revenue']} BDT\n\n"
                f"🔐 Force Sub: {'🟢 ON' if state.force_sub_enabled else '🔴 OFF'}\n"
                f"🔒 Lock: {'🔒 ON' if state.bot_locked else '🔓 OFF'}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=admin_kb()
            )

        elif data == "adm_users":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            users = db.get_all_users()
            t = f"👥 <b>Users ({len(users)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for u in users[:30]:
                st = "🚫" if u['is_banned'] else "💎" if u['plan'] != 'free' else "✅"
                t += f"  {st} <code>{u['user_id']}</code> {(u['full_name'] or '-')[:15]} [{u['plan']}]\n"
            if len(users) > 30:
                t += f"\n  ... +{len(users) - 30} more"
            safe_edit(t + "\n━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id,
                      reply_markup=back_btn("menu_admin", "🔙 Admin"))

        elif data == "adm_stats":
            safe_answer(call.id)
            s = db.stats()
            ss = sys_stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            safe_edit(
                f"📊 <b>Full Statistics</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"<b>Users:</b>\n"
                f"  👥 Total: {s['users']}\n"
                f"  📅 Today: {s['today']}\n"
                f"  💎 Active Subs: {s['active_subs']}\n"
                f"  🚫 Banned: {s['banned']}\n\n"
                f"<b>System:</b>\n"
                f"  🖥️ CPU: {ss['cpu']}%\n"
                f"  🧠 RAM: {ss['mem']}%\n"
                f"  💾 Disk: {ss['disk']}%\n"
                f"  ⏱️ Up: {ss['up']}\n\n"
                f"<b>Finance:</b>\n"
                f"  💰 Revenue: {s['revenue']} BDT\n"
                f"  💳 Pending: {s['pending']}\n"
                f"  🤖 Running: {rn}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_btn("menu_admin", "🔙 Admin")
            )

        elif data == "adm_payments":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            pays = db.pending_pay()
            t = f"💳 <b>Pending Payments ({len(pays)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            if not pays:
                t += "✅ No pending payments!\n"
                safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id,
                          reply_markup=back_btn("menu_admin", "🔙 Admin"))
                return
            for p in pays[:15]:
                pu = db.get_user(p['user_id'])
                pname = pu['full_name'] if pu else str(p['user_id'])
                t += (
                    f"🆔 #{p['payment_id']} | 👤 {pname}\n"
                    f"  💰 {p['amount']} BDT | {p['method']} | {p['plan']}\n"
                    f"  🔖 TRX: <code>{p['transaction_id']}</code>\n\n"
                )
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id)
            for p in pays[:10]:
                safe_send(uid,
                    f"💳 Payment #{p['payment_id']}\n"
                    f"👤 <code>{p['user_id']}</code>\n"
                    f"💰 {p['amount']} BDT | {p['method']}\n"
                    f"📦 {p['plan']} | TRX: <code>{p['transaction_id']}</code>",
                    reply_markup=pay_approve_kb(p['payment_id'])
                )

        elif data == "adm_broadcast":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'broadcast'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"📢 <b>BROADCAST</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send your broadcast message now.\n"
                f"It will be sent to ALL users.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_addsub":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_addsub_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"➕ <b>ADD SUBSCRIPTION</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send the User ID:\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data.startswith("adm_setplan:"):
            if not state.is_admin(uid):
                return
            parts = data.split(":")
            plan = parts[1]
            target = int(parts[2])
            state.set_state(uid, {'action': 'adm_addsub_days', 'target': target, 'plan': plan})
            m = types.InlineKeyboardMarkup(row_width=3)
            m.add(
                types.InlineKeyboardButton("7 Days", callback_data=f"adm_quicksub:{plan}:{target}:7"),
                types.InlineKeyboardButton("30 Days", callback_data=f"adm_quicksub:{plan}:{target}:30"),
                types.InlineKeyboardButton("90 Days", callback_data=f"adm_quicksub:{plan}:{target}:90")
            )
            m.add(
                types.InlineKeyboardButton("180 Days", callback_data=f"adm_quicksub:{plan}:{target}:180"),
                types.InlineKeyboardButton("365 Days", callback_data=f"adm_quicksub:{plan}:{target}:365"),
                types.InlineKeyboardButton("♾ Lifetime", callback_data=f"adm_quicksub:lifetime:{target}:0")
            )
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"📅 <b>Select Duration</b>\n\n"
                f"👤 User: <code>{target}</code>\n"
                f"📦 Plan: {PLAN_LIMITS.get(plan, {}).get('name', plan)}\n\n"
                f"Choose below or send custom days:",
                chat_id, msg_id, reply_markup=m
            )
            safe_answer(call.id)

        elif data.startswith("adm_quicksub:"):
            if not state.is_admin(uid):
                return
            parts = data.split(":")
            plan = parts[1]
            target = int(parts[2])
            days = int(parts[3])
            state.clear_state(uid)
            if days == 0 or plan == 'lifetime':
                db.set_sub(target, 'lifetime')
                plan_name = "👑 Lifetime"
                dur_text = "Lifetime"
            else:
                db.set_sub(target, plan, days)
                plan_name = PLAN_LIMITS.get(plan, {}).get('name', plan)
                dur_text = f"{days} days"
            safe_answer(call.id, "✅ Done!")
            safe_edit(
                f"✅ <b>Subscription Added!</b>\n\n"
                f"👤 User: <code>{target}</code>\n"
                f"📦 Plan: {plan_name}\n"
                f"📅 Duration: {dur_text}",
                chat_id, msg_id, reply_markup=back_btn("menu_admin", "🔙 Admin")
            )
            db.admin_log(uid, 'add_sub', target, f"{plan}/{dur_text}")
            safe_send(target,
                f"🎉 <b>Plan Upgraded!</b>\n📦 {plan_name}\n📅 {dur_text}\n{BRAND_FOOTER}")

        elif data == "adm_remsub":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_remsub_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"➖ <b>REMOVE SUBSCRIPTION</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send the User ID:\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_ban":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_ban_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"🚫 <b>BAN USER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send: USER_ID [REASON]\n"
                f"Example: 123456789 Spam\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_unban":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_unban_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"✅ <b>UNBAN USER</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send the User ID:\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data.startswith("adm_ban_direct:"):
            if not state.is_admin(uid):
                return
            target = int(data.split(":")[1])
            db.ban(target, "Banned from admin panel")
            db.admin_log(uid, 'ban', target)
            for b in db.get_bots(target):
                sk = f"{target}_{b['bot_name']}"
                if sk in bot_scripts:
                    kill_tree(bot_scripts[sk])
                    cleanup_script(sk)
                db.update_bot(b['bot_id'], status='stopped')
            safe_answer(call.id, "🚫 Banned!")
            safe_send(target, f"🚫 <b>You have been banned!</b>\nContact {YOUR_USERNAME}")

        elif data.startswith("adm_unban_direct:"):
            if not state.is_admin(uid):
                return
            target = int(data.split(":")[1])
            db.unban(target)
            db.admin_log(uid, 'unban', target)
            safe_answer(call.id, "✅ Unbanned!")
            safe_send(target, "✅ You have been unbanned!")

        elif data == "adm_channels":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            channels = db.get_all_channels()
            t = (
                f"📢 <b>Force Subscribe Channels</b>\n"
                f"Status: {'🟢 ON' if state.force_sub_enabled else '🔴 OFF'}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
            )
            if channels:
                for ch in channels:
                    st = "🟢" if ch['is_active'] else "🔴"
                    t += f"  {st} @{ch['channel_username']} — {ch['channel_name']}\n"
            else:
                t += "  No custom channels.\n  Default: @developer_apon_07\n"
            t += "\n━━━━━━━━━━━━━━━━━━━━\n👇 Click channel to toggle, or add/remove."
            safe_edit(t, chat_id, msg_id, reply_markup=channels_manage_kb())

        elif data.startswith("ch_toggle:"):
            if not state.is_admin(uid):
                return
            cid_ch = int(data.split(":")[1])
            ns = db.toggle_channel(cid_ch)
            if ns is not None:
                safe_answer(call.id, f"{'🟢 Enabled' if ns else '🔴 Disabled'}!")
            call.data = "adm_channels"
            handle_callback(call)

        elif data == "ch_add":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'ch_add'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="adm_channels"))
            safe_edit(
                f"➕ <b>Add Channel</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send: @username [Channel Name]\n"
                f"Example: @mychannel My Channel\n\n"
                f"⚠️ Bot must be admin in the channel!\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "ch_remove":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'ch_remove'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="adm_channels"))
            safe_edit(
                f"🗑 <b>Remove Channel</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send the channel username:\n"
                f"Example: developer_apon_07\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_promo":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            promos = db.all_promos()
            t = f"🎟 <b>Promo Codes ({len(promos)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for p in promos[:15]:
                st = "🟢" if p['is_active'] else "🔴"
                t += f"  {st} <code>{p['code']}</code> — {p['discount_pct']}% off — {p['used_count']}/{p['max_uses']} used\n"
            if not promos:
                t += "  No promo codes yet.\n"
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(types.InlineKeyboardButton("➕ Create Promo", callback_data="adm_promo_create"))
            m.add(types.InlineKeyboardButton("🔙 Admin", callback_data="menu_admin"))
            safe_edit(t + "\n━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=m)

        elif data == "adm_promo_create":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_promo_create'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="adm_promo"))
            safe_edit(
                f"➕ <b>Create Promo Code</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send: CODE DISCOUNT% MAX_USES\n"
                f"Example: SAVE50 50 100\n\n"
                f"This creates code SAVE50 with 50% discount, max 100 uses.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_tickets":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            tickets = db.open_tickets()
            t = f"🎫 <b>Support Tickets ({len(tickets)})</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            m = types.InlineKeyboardMarkup(row_width=1)
            for tk in tickets[:15]:
                tu = db.get_user(tk['user_id'])
                tname = tu['full_name'] if tu else str(tk['user_id'])
                t += (
                    f"🎫 #{tk['ticket_id']} | 👤 {tname}\n"
                    f"  📝 {tk['message'][:50]}...\n"
                    f"  📅 {tk['created_at'][:16]}\n\n"
                )
                m.add(types.InlineKeyboardButton(
                    f"💬 Reply #{tk['ticket_id']}", callback_data=f"adm_ticket_reply:{tk['ticket_id']}"
                ))
            if not tickets:
                t += "  ✅ No open tickets!\n"
            m.add(types.InlineKeyboardButton("🔙 Admin", callback_data="menu_admin"))
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id, reply_markup=m)

        elif data.startswith("adm_ticket_reply:"):
            if not state.is_admin(uid):
                return
            tid = int(data.split(":")[1])
            ticket = db.get_ticket(tid)
            if not ticket:
                return safe_answer(call.id, "❌ Ticket not found!", show_alert=True)
            safe_answer(call.id)
            state.set_state(uid, {'action': 'ticket_reply', 'ticket_id': tid})
            tu = db.get_user(ticket['user_id'])
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="adm_tickets"))
            safe_edit(
                f"💬 <b>Reply to Ticket #{tid}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 From: {tu['full_name'] if tu else ticket['user_id']}\n"
                f"📝 Message:\n<i>{ticket['message'][:300]}</i>\n\n"
                f"📝 Send your reply now:\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_system":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            ss = sys_stats()
            rn = len([k for k in bot_scripts if is_running(k)])
            total_bots = len(bot_scripts)
            safe_edit(
                f"🖥 <b>SYSTEM INFO</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🖥️ CPU: {ss['cpu']}%\n"
                f"🧠 RAM: {ss['mem']}% ({ss['mem_used']}/{ss['mem_total']})\n"
                f"💾 Disk: {ss['disk']}% ({ss['disk_used']}/{ss['disk_total']})\n"
                f"⏱️ Uptime: {ss['up']}\n\n"
                f"🤖 Total Bot Entries: {total_bots}\n"
                f"🟢 Running: {rn}\n"
                f"🔴 Stopped: {total_bots - rn}\n\n"
                f"🐍 Python: {sys.version.split()[0]}\n"
                f"📂 Base: {BASE_DIR[:40]}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_btn("menu_admin", "🔙 Admin")
            )

        elif data == "adm_stopall":
            if not state.is_admin(uid):
                return
            safe_answer(call.id, "🛑 Stopping all bots...")
            count = 0
            for sk in list(bot_scripts.keys()):
                i = bot_scripts.get(sk)
                if i:
                    kill_tree(i)
                    bid = i.get('bot_id')
                    if bid:
                        db.update_bot(bid, status='stopped')
                    cleanup_script(sk)
                    count += 1
            db.admin_log(uid, 'stop_all', details=f"stopped:{count}")
            safe_edit(
                f"🛑 <b>All Bots Stopped!</b>\n\n✅ Stopped: {count} bots\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=back_btn("menu_admin", "🔙 Admin")
            )

        elif data == "adm_backup":
            if not state.is_admin(uid):
                return
            safe_answer(call.id, "💾 Creating backup...")
            try:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                bp = os.path.join(BACKUP_DIR, f"bk_{ts}.db")
                shutil.copy2(DB_PATH, bp)
                with open(bp, 'rb') as f:
                    bot.send_document(uid, f, caption=f"💾 Database Backup\n📅 {ts}\n{BRAND_FOOTER}")
                db.admin_log(uid, 'backup', details=ts)
            except Exception as e:
                safe_send(uid, f"❌ Backup failed: {e}")

        elif data == "adm_logs":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            logs = db.get_admin_logs(20)
            t = f"📜 <b>Admin Logs</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
            for l in logs:
                t += f"  🕐 {l['created_at'][:16]}\n"
                t += f"  👤 <code>{l['admin_id']}</code> → {l['action']}\n"
                if l.get('target_user'):
                    t += f"  🎯 Target: <code>{l['target_user']}</code>\n"
                if l.get('details'):
                    t += f"  📝 {l['details'][:40]}\n"
                t += "\n"
            if not logs:
                t += "  No logs yet.\n"
            safe_edit(t + "━━━━━━━━━━━━━━━━━━━━", chat_id, msg_id,
                      reply_markup=back_btn("menu_admin", "🔙 Admin"))

        elif data == "adm_give":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_give_balance'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"💰 <b>Give Balance</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send: USER_ID AMOUNT\n"
                f"Example: 123456789 500\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_userinfo":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_userinfo_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"🔍 <b>User Info</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send the User ID:\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_notify":
            if not state.is_admin(uid):
                return
            safe_answer(call.id)
            state.set_state(uid, {'action': 'adm_notify_uid'})
            m = types.InlineKeyboardMarkup()
            m.add(types.InlineKeyboardButton("❌ Cancel", callback_data="menu_admin"))
            safe_edit(
                f"🔔 <b>Send Notification</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 Send: USER_ID MESSAGE\n"
                f"Example: 123456789 Your bot is ready!\n━━━━━━━━━━━━━━━━━━━━",
                chat_id, msg_id, reply_markup=m
            )

        elif data == "adm_fsub_toggle":
            if not state.is_admin(uid):
                return
            state.force_sub_enabled = not state.force_sub_enabled
            st = "🟢 ON" if state.force_sub_enabled else "🔴 OFF"
            safe_answer(call.id, f"Force Subscribe: {st}", show_alert=True)
            db.admin_log(uid, 'toggle_fsub', details=st)
            # Refresh admin panel
            call.data = "menu_admin"
            handle_callback(call)

        elif data == "adm_lock_toggle":
            if not state.is_admin(uid):
                return
            state.bot_locked = not state.bot_locked
            st = "🔒 LOCKED" if state.bot_locked else "🔓 OPEN"
            safe_answer(call.id, f"Bot: {st}", show_alert=True)
            db.admin_log(uid, 'toggle_lock', details=st)
            call.data = "menu_admin"
            handle_callback(call)

        # ═══════════════════════════════════════
        #  UNKNOWN CALLBACK FALLBACK
        # ═══════════════════════════════════════
        else:
            safe_answer(call.id, "⚠️ Unknown action!", show_alert=False)
            logger.warning(f"Unknown callback: {data} from {uid}")

    except Exception as e:
        logger.error(f"Callback error [{data}]: {e}", exc_info=True)
        forward_crash(f"callback:{data}", e, uid)
        safe_answer(call.id, "❌ An error occurred!", show_alert=True)
        try:
            safe_edit(
                f"❌ <b>Error occurred!</b>\n\n"
                f"Please try again or go back.\n{BRAND_FOOTER}",
                chat_id, msg_id, reply_markup=back_btn()
            )
        except:
            pass


# ═══════════════════════════════════════════════════
#  PHOTO HANDLER (Payment screenshots)
# ═══════════════════════════════════════════════════
@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    uid = msg.from_user.id
    s = state.get_pay_state(uid)
    if s and s.get('step') == 'wait_trx':
        try:
            trx = f"SCREENSHOT_{datetime.now().strftime('%H%M%S')}"
            pid = db.add_pay(uid, s['amount'], s['method'], trx, s['plan'], 30)
            state.clear_pay_state(uid)

            safe_send(uid,
                f"✅ <b>PAYMENT SUBMITTED!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🆔 #{pid}\n"
                f"📸 Screenshot received\n"
                f"⏳ Waiting for approval...\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                reply_markup=back_btn()
            )

            u = db.get_user(uid)
            for aid in state.admin_ids:
                try:
                    bot.forward_message(aid, uid, msg.message_id)
                except:
                    pass
                safe_send(aid,
                    f"💳 <b>Payment #{pid}</b> (Screenshot)\n"
                    f"👤 {u['full_name'] if u else uid} (<code>{uid}</code>)\n"
                    f"💰 {s['amount']} BDT | {s['method']} | {s['plan']}",
                    reply_markup=pay_approve_kb(pid)
                )
        except Exception as e:
            forward_crash("handle_photo", e, uid)
            state.clear_pay_state(uid)


# ═══════════════════════════════════════════════════
#  GLOBAL ERROR HANDLER
# ═══════════════════════════════════════════════════
# Middleware disabled - not needed

# ═══════════════════════════════════════════════════
#  CLEANUP ON EXIT
# ═══════════════════════════════════════════════════
def cleanup():
    logger.info("🛑 Shutting down...")
    for sk in list(bot_scripts.keys()):
        i = bot_scripts.get(sk)
        if i:
            try:
                kill_tree(i)
            except:
                pass
            bid = i.get('bot_id')
            if bid:
                try:
                    db.update_bot(bid, status='stopped')
                except:
                    pass
            cleanup_script(sk)
    logger.info("✅ Cleanup complete")


atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ═══════════════════════════════════════════════════
#  MAIN STARTUP
# ═══════════════════════════════════════════════════
def main():
    global ERROR_CHAT_ID

    logger.info(f"{'=' * 50}")
    logger.info(f"  {BRAND_TAG}")
    logger.info(f"  Starting up...")
    logger.info(f"{'=' * 50}")

    # Set error chat
    ERROR_CHAT_ID = OWNER_ID

    # Init error bot
    init_error_bot()

    # Start Flask keep-alive
    keep_alive()
    logger.info("✅ Flask keep-alive started")

    # Start background threads
    threading.Thread(target=thread_monitor, daemon=True).start()
    logger.info("✅ Bot monitor started")

    threading.Thread(target=thread_backup, daemon=True).start()
    logger.info("✅ Auto-backup started")

    threading.Thread(target=thread_expiry, daemon=True).start()
    logger.info("✅ Expiry checker started")

    # Auto-restart previously running bots
    try:
        running_bots = db.exe(
            "SELECT * FROM bots WHERE status='running'", fetch=True
        ) or []
        for b in running_bots:
            logger.info(f"🔄 Auto-restarting bot #{b['bot_id']}: {b['bot_name']}")
            db.update_bot(b['bot_id'], status='starting')
            threading.Thread(
                target=run_bot_script,
                args=(b['bot_id'], b['user_id']),
                daemon=True
            ).start()
            time.sleep(2)
    except Exception as e:
        logger.error(f"Auto-restart error: {e}")
        forward_error("AUTO_RESTART", e)

    # Notify owner
    safe_send(OWNER_ID,
        f"🚀 <b>{BRAND_TAG} STARTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ All systems online\n"
        f"📊 DB: OK\n"
        f"🌐 Flask: OK\n"
        f"🔍 Monitor: OK\n"
        f"💾 Backup: OK\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=main_menu_kb(OWNER_ID)
    )

    logger.info("🚀 Bot polling started!")

    # Start polling with auto-reconnect
    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=['message', 'callback_query'],
                skip_pending=True
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt — shutting down")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            forward_error("POLLING_CRASH", e)
            logger.info("🔄 Reconnecting in 10 seconds...")
            time.sleep(10)


if __name__ == '__main__':
    main()
