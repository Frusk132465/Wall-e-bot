import telebot
import random
import sqlite3
import time

# ================== DATABASE ==================
db = sqlite3.connect("wall_e.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    score INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS warns (
    user_id INTEGER PRIMARY KEY,
    count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subs (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    expires INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    chat_id INTEGER PRIMARY KEY,
    owner_id INTEGER,
    expires INTEGER
)
""")

db.commit()

# ================== BOT CONFIG ==================
TOKEN = "8563881057:AAHbYqw_WbEtbF66-an9scrqyRp2ITi6eWM"
bot = telebot.TeleBot(TOKEN)

OWNER_ID = 6780552832  # آیدی عددی خودت

# ================== HELPERS ==================
def channel_active(chat_id):
    cursor.execute(
        "SELECT expires FROM channels WHERE chat_id = ?",
        (chat_id,)
    )
    row = cursor.fetchone()

    if not row:
        return False

    if time.time() > row[0]:
        cursor.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
        db.commit()
        return False

    return True


def check_channel(message):
    if message.chat.type in ["group", "supergroup", "channel"]:
        return channel_active(message.chat.id)
    return True


def add_score(user_id, name, points):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, name, score) VALUES (?, ?, 0)",
        (user_id, name)
    )
    cursor.execute(
        "UPDATE users SET score = score + ? WHERE user_id = ?",
        (points, user_id)
    )
    db.commit()


def is_vip(user_id):
    cursor.execute(
        "SELECT expires FROM subs WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        return False

    if time.time() > row[0]:
        cursor.execute("DELETE FROM subs WHERE user_id = ?", (user_id,))
        db.commit()
        return False

    return True

# ================== OWNER COMMANDS ==================
@bot.message_handler(commands=["addchannel"])
def add_channel(message):
    if message.from_user.id != OWNER_ID:
        return

    if message.chat.type not in ["group", "supergroup", "channel"]:
        bot.reply_to(message, "❌ Use inside a group or channel")
        return

    try:
        days = int(message.text.split()[1])
    except:
        bot.reply_to(message, "Usage: /addchannel <days>")
        return

    expires = int(time.time()) + days * 86400

    cursor.execute(
        "INSERT OR REPLACE INTO channels (chat_id, owner_id, expires) VALUES (?, ?, ?)",
        (message.chat.id, OWNER_ID, expires)
    )
    db.commit()

    bot.reply_to(message, f"✅ Channel activated for {days} days")


@bot.message_handler(commands=["addvip"])
def addvip(message):
    if message.from_user.id != OWNER_ID:
        return

    try:
        _, user_id, days = message.text.split()
        user_id = int(user_id)
        days = int(days)
    except:
        bot.reply_to(message, "Usage: /addvip user_id days")
        return

    expires = int(time.time()) + days * 86400

    cursor.execute(
        "INSERT OR REPLACE INTO subs (user_id, name, expires) VALUES (?, ?, ?)",
        (user_id, "VIP", expires)
    )
    db.commit()

    bot.reply_to(message, "✅ VIP added")


# ================== PUBLIC COMMANDS ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🤖 Wall-E is online!\n\n"
        "/rps\n"
        "/leaderboard\n"
        "/balance\n"
        "/vipdice (VIP)\n"
        "/roulette (VIP)\n"
        "/guess (VIP)\n"
        "/gamble (VIP)"
    )


@bot.message_handler(commands=["balance"])
def balance(message):
    cursor.execute(
        "SELECT score FROM users WHERE user_id = ?",
        (message.from_user.id,)
    )
    row = cursor.fetchone()
    score = row[0] if row else 0

    bot.reply_to(message, f"💰 Balance: {score}")


@bot.message_handler(commands=["rps"])
def rps(message):
    if not check_channel(message):
        return

    user = random.choice(["rock", "paper", "scissors"])
    botc = random.choice(["rock", "paper", "scissors"])

    if user == botc:
        points = 0
        result = "🤝 Draw"
    elif (user == "rock" and botc == "scissors") or \
         (user == "paper" and botc == "rock") or \
         (user == "scissors" and botc == "paper"):
        points = 1
        result = "🎉 You win +1"
    else:
        points = -1
        result = "😈 You lose -1"

    add_score(message.from_user.id, message.from_user.first_name, points)

    bot.reply_to(message, f"You: {user}\nWall-E: {botc}\n{result}")


@bot.message_handler(commands=["leaderboard"])
def leaderboard(message):
    if not check_channel(message):
        return

    cursor.execute(
        "SELECT name, score FROM users ORDER BY score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    if not rows:
        bot.reply_to(message, "Empty leaderboard")
        return

    text = "🏆 Leaderboard\n\n"
    for i, (name, score) in enumerate(rows, 1):
        text += f"{i}. {name} — {score}\n"

    bot.reply_to(message, text)

# ================== VIP GAMES ==================
@bot.message_handler(commands=["vipdice"])
def vipdice(message):
    if not check_channel(message):
        return
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "🔒 VIP only")
        return

    roll = random.randint(1, 6)
    bot.reply_to(message, f"🎲 Dice: {roll}")


@bot.message_handler(commands=["roulette"])
def roulette(message):
    if not check_channel(message):
        return
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "🔒 VIP only")
        return

    uid = message.from_user.id
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()

    if not row or row[0] <= 0:
        bot.reply_to(message, "❌ No score")
        return

    if random.randint(1, 6) == 1:
        cursor.execute("UPDATE users SET score = 0 WHERE user_id = ?", (uid,))
        db.commit()
        bot.reply_to(message, "🔫 BANG! Lost everything")
    else:
        cursor.execute("UPDATE users SET score = score + 2 WHERE user_id = ?", (uid,))
        db.commit()
        bot.reply_to(message, "😮 Click… +2 points")


@bot.message_handler(commands=["guess"])
def guess(message):
    if not check_channel(message):
        return
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "🔒 VIP only")
        return

    try:
        g = int(message.text.split()[1])
    except:
        bot.reply_to(message, "Usage: /guess 1-10")
        return

    n = random.randint(1, 10)

    if g == n:
        cursor.execute(
            "UPDATE users SET score = score + 4 WHERE user_id = ?",
            (message.from_user.id,)
        )
        db.commit()
        bot.reply_to(message, "🎯 Correct +4")
    else:
        bot.reply_to(message, f"❌ Wrong, was {n}")


@bot.message_handler(commands=["gamble"])
def gamble(message):
    if not check_channel(message):
        return
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "🔒 VIP only")
        return

    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Usage: /gamble amount red|black")
        return

    amount = int(parts[1])
    choice = parts[2].lower()

    cursor.execute("SELECT score FROM users WHERE user_id = ?", (message.from_user.id,))
    score = cursor.fetchone()[0]

    if score < amount:
        bot.reply_to(message, "❌ NOT ENOUGH SCORE")
        return

    # house edge
    bot_choice = choice if random.random() > 0.55 else ("red" if choice == "black" else "black")

    if choice == bot_choice:
        cursor.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (amount, message.from_user.id))
        db.commit()
        bot.reply_to(message, f"✅ WON +{amount}")
    else:
        cursor.execute("UPDATE users SET score = score - ? WHERE user_id = ?", (amount, message.from_user.id))
        db.commit()
        bot.reply_to(message, f"❌ LOST -{amount}")

# ================== RUN ==================
print("🤖 Wall-E is running…")
bot.infinity_polling()
