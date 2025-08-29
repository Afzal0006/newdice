from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from pymongo import MongoClient
import random

# ===== Config =====
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 7363327309  # Apna Telegram user ID

# ===== MongoDB setup =====
client = MongoClient(MONGO_URI)
db = client["dicebot"]
players_collection = db["players"]

# ===== Game status =====
game_active = False
fixed_dice_roll = None

# ===== Commands =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this command!")
        return

    game_active = True
    players_collection.delete_many({})
    await update.message.reply_text(
        "🎲 Dice game started!\nUsers, pick your number (1-6) using /dice <number>"
    )

async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game_active:
        await update.message.reply_text("No active game! Please wait for the owner to start.")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /dice <number between 1-6>")
        return

    number = int(context.args[0])
    if number < 1 or number > 6:
        await update.message.reply_text("Number must be between 1 and 6!")
        return

    user_id = update.message.from_user.id
    username = update.message.from_user.first_name

    # Check if user already picked
    if players_collection.find_one({"user_id": user_id}):
        await update.message.reply_text("❌ You have already picked a number for this game!")
        return

    # Save user's pick
    players_collection.insert_one({
        "user_id": user_id,
        "username": username,
        "chosen_number": number
    })

    await update.message.reply_text(f"{username} picked {number}")

# ===== Owner DM command to set fixed dice result =====
async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global fixed_dice_roll
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this command!")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /result <number 1-6>")
        return

    number = int(context.args[0])
    if number < 1 or number > 6:
        await update.message.reply_text("Number must be between 1-6!")
        return

    fixed_dice_roll = number
    await update.message.reply_text(f"✅ Dice result set to {fixed_dice_roll} for next /result in group.")

# ===== Group /result command =====
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active, fixed_dice_roll

    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can use this command!")
        return

    if not game_active:
        await update.message.reply_text("No active game!")
        return

    # Use fixed dice roll if set, else random
    dice_roll = fixed_dice_roll if fixed_dice_roll else random.randint(1, 6)

    # Fetch players from MongoDB
    players = list(players_collection.find({}))

    winners = [p["username"] for p in players if p["chosen_number"] == dice_roll]
    losers = [p["username"] for p in players if p["chosen_number"] != dice_roll]

    # Prepare message
    result_msg = f"🎲 Dice rolled: {dice_roll}\n\n"
    result_msg += "🏆 Winners:\n" + ("\n".join(winners) if winners else "None") + "\n\n"
    result_msg += "❌ Losers:\n" + ("\n".join(losers) if losers else "None")

    await update.message.reply_text(result_msg)

    # Reset game
    game_active = False
    players_collection.delete_many({})
    fixed_dice_roll = None

# ===== Main =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Owner commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("result", set_result))  # DM command to set fixed dice

# Group/user commands
app.add_handler(CommandHandler("dice", dice))
app.add_handler(CommandHandler("show_result", result))  # Group /result uses different command to avoid conflict

print("Bot is running...")
app.run_polling()
