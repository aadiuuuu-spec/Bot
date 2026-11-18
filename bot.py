import asyncio, json, logging, os, re, urllib.request
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatType
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
CREATOR = os.getenv("CREATOR_USERNAME", "@II_YUTA_II")
TARGET_FILE = Path("targets.json")
DICT_FILE = Path("words_alpha.txt")
DICT_URL = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("group-toolkit")
targets = defaultdict(set)
active_games = set()
WORDS = set()

def load_targets():
    global targets
    try:
        data = json.loads(TARGET_FILE.read_text())
        targets = defaultdict(set, {str(k): set(map(int, v)) for k, v in data.items()})
    except (OSError, ValueError, TypeError):
        targets = defaultdict(set)

def save_targets():
    tmp = TARGET_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({k: sorted(v) for k, v in targets.items()}, indent=2))
    tmp.replace(TARGET_FILE)

def load_words():
    try:
        if not DICT_FILE.exists():
            urllib.request.urlretrieve(DICT_URL, DICT_FILE)
        return {x.strip().lower() for x in DICT_FILE.read_text(errors="ignore").splitlines()
                if 3 <= len(x.strip()) <= 7 and x.strip().isalpha()}
    except Exception:
        log.exception("Dictionary download failed")
        return set()

def group(update):
    return bool(update.effective_chat and update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))

async def say(update, text, **kwargs):
    if update.effective_message:
        await update.effective_message.reply_text(text, **kwargs)

async def admin(update, context):
    if not group(update) or not update.effective_user:
        return False
    try:
        m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return m.status in ("administrator", "creator")
    except TelegramError:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await say(update, "╭━━━「 GROUP TOOLKIT 」━━━╮\n"
        "Start the bot and add it to your group.\n\n"
        "/target — reply to a user; auto-delete their new messages\n"
        "/release — stop targeting a user\n/targets — list targets\n"
        "/ban — reply to a user to ban (admins only)\n/banall — API limitation info\n"
        "/search [3-7] — solve a WordSeek letter grid\n/g [3-7] — solver helper\n"
        "/s — stop helper\n/raw — inspect replied message data\n/help — guide\n\n"
        f"Made by: {CREATOR}\n╰━━━━━━━━━━━━━━━━━━━━━━╯")

async def help_cmd(update, context):
    await say(update, "Use /target and /release by replying to a member. /ban is reply-based and admin-only. "
        "/search or /g reads a replied letter grid. /raw shows visible message data. "
        "Bot needs Delete Messages and Ban Users permissions. Disable privacy mode in @BotFather "
        "if it must read ordinary group messages.")

async def get_target(update, context):
    msg = update.effective_message
    if msg and msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    if context.args:
        v = context.args[0]
        try:
            return await context.bot.get_chat(int(v) if v.isdigit() else v)
        except TelegramError:
            return None
    return None

async def target_cmd(update, context):
    if not group(update): return await say(update, "Use in a group.")
    if not await admin(update, context): return await say(update, "Only group admins can use this.")
    u = await get_target(update, context)
    if not u or getattr(u, "is_bot", False): return await say(update, "Reply to a user's message or provide numeric USER_ID.")
    targets[str(update.effective_chat.id)].add(int(u.id)); save_targets()
    await say(update, f"Target enabled for {getattr(u, 'first_name', 'user')} ({u.id}).")

async def release_cmd(update, context):
    if not group(update): return await say(update, "Use in a group.")
    if not await admin(update, context): return await say(update, "Only group admins can use this.")
    u = await get_target(update, context)
    if not u: return await say(update, "Reply to the user or provide numeric USER_ID.")
    targets[str(update.effective_chat.id)].discard(int(u.id)); save_targets()
    await say(update, f"Target released for {getattr(u, 'first_name', 'user')} ({u.id}).")

async def targets_cmd(update, context):
    if not group(update): return await say(update, "Use in a group.")
    ids = sorted(targets.get(str(update.effective_chat.id), set()))
    await say(update, "No active targets." if not ids else "Target user IDs:\n" + "\n".join(map(str, ids)))

async def delete_targets(update, context):
    m, c, u = update.effective_message, update.effective_chat, update.effective_user
    if m and c and u and c.type in (ChatType.GROUP, ChatType.SUPERGROUP) and u.id in targets.get(str(c.id), set()):
        try: await m.delete()
        except TelegramError as e: log.warning("Delete failed: %s", e)

async def ban_cmd(update, context):
    if not group(update): return await say(update, "Use in a group.")
    if not await admin(update, context): return await say(update, "Only group admins can use /ban.")
    m = update.effective_message
    u = m.reply_to_message.from_user if m and m.reply_to_message else None
    if not u: return await say(update, "Reply to the user's message with /ban.")
    if u.id == context.bot.id: return await say(update, "Cannot ban myself.")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, u.id)
        await say(update, f"Banned {u.first_name}.")
    except TelegramError as e: await say(update, f"Ban failed: {e}")

async def banall_cmd(update, context):
    if not group(update): return await say(update, "Use in a group.")
    if not await admin(update, context): return await say(update, "Only group admins can use /banall.")
    await say(update, "Telegram Bot API does not expose a complete group member list, so a true /banall is not technically available. No mass-ban was performed.")

def parse_board(text):
    rows = []
    for line in (text or "").splitlines():
        row = re.findall(r"[A-Za-z]", line)
        if 2 <= len(row) <= 12: rows.append([x.lower() for x in row])
    if len(rows) >= 2:
        w = min(map(len, rows))
        return [r[:w] for r in rows if len(r) >= w]
    letters = re.findall(r"[A-Za-z]", text or "")
    n = int(len(letters) ** .5)
    return [letters[i:i+n] for i in range(0, len(letters), n)] if n >= 2 and n*n == len(letters) else []

def solve(board, minimum=3):
    if not board or not WORDS: return []
    h, w, found = len(board), len(board[0]), set()
    for r in range(h):
        for c in range(w):
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if not (dr or dc): continue
                    chars, y, x = [], r, c
                    while 0 <= y < h and 0 <= x < w and len(chars) < 7:
                        chars.append(board[y][x]); word = "".join(chars)
                        if len(word) >= minimum and word in WORDS: found.add(word)
                        y += dr; x += dc
    return sorted(found, key=lambda x: (-len(x), x))

async def search_cmd(update, context):
    m = update.effective_message
    source = ""
    if m and m.reply_to_message:
        source = m.reply_to_message.text or m.reply_to_message.caption or ""
    if context.args and not (len(context.args) == 1 and context.args[0].isdigit()):
        source = " ".join(context.args)
    minimum = int(context.args[0]) if context.args and context.args[0].isdigit() else 3
    minimum = max(3, min(7, minimum))
    board = parse_board(source)
    if not board: return await say(update, "Reply to a letter grid or send /search followed by rows, e.g. ABCD\nEFGH\nIJKL.")
    found = solve(board, minimum)
    if not found: return await say(update, "No matching words found. Check the grid and dictionary.")
    await say(update, f"Found {len(found)} words (up to 60):\n" + ", ".join(found[:60]))

async def game_cmd(update, context):
    if not group(update): return await say(update, "Use /g in a group.")
    active_games.add((update.effective_chat.id, update.effective_user.id))
    await search_cmd(update, context)
    await say(update, "Helper started. It finds words from a visible grid; it cannot submit moves to another bot/game.")

async def stop_cmd(update, context):
    if group(update): active_games.discard((update.effective_chat.id, update.effective_user.id))
    await say(update, "Solver helper stopped.")

async def raw_cmd(update, context):
    m = update.effective_message
    if not m or not m.reply_to_message: return await say(update, "Reply to a message with /raw.")
    x = m.reply_to_message
    text = x.text or x.caption or "[no text]"
    info = (f"Message ID: {x.message_id}\nChat ID: {x.chat_id}\n"
        f"Sender ID: {x.from_user.id if x.from_user else 'unknown'}\n"
        f"Date: {x.date.isoformat() if x.date else 'unknown'}\n"
        f"Text: {text[:2500]}\nEntities: {len(x.entities or x.caption_entities or [])}\n"
        f"Media: {'yes' if x.effective_attachment else 'no'}")
    await say(update, info)

async def post_init(app):
    global WORDS
    load_targets()
    WORDS = await asyncio.to_thread(load_words)
    log.info("Loaded %d words", len(WORDS))

async def on_error(update, context):
    log.exception("Unhandled error", exc_info=context.error)

def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN is missing. Add it in Railway Variables.")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    for name, fn in [
        ("start", start), ("help", help_cmd), ("target", target_cmd),
        ("release", release_cmd), ("targets", targets_cmd), ("ban", ban_cmd),
        ("banall", banall_cmd), ("search", search_cmd), ("g", game_cmd),
        ("s", stop_cmd), ("raw", raw_cmd)
    ]: app.add_handler(CommandHandler(name, fn))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, delete_targets))
    app.add_error_handler(on_error)
    log.info("Group Toolkit is starting")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
