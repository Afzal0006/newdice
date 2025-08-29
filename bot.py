import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters
from pymongo import MongoClient

# ===== Config =====
BOT_TOKEN = "8357734886:AAHQi1zmj9q8B__7J-2dyYUWVTQrMRr65Dc"
MONGO_URI = "mongodb+srv://afzal99550:afzal99550@cluster0.aqmbh9q.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
OWNER_ID = 7363327309

# ===== MongoDB setup =====
client = MongoClient(MONGO_URI)
db = client["dicebot"]
players_collection = db["players"]

# ===== Game status =====
game_active = False
fixed_dice_roll = None

# ===== Dice images URLs =====
dice_images = {
    1: "https://i.ibb.co/xqVxWWZt/x.jpg",
    2: "https://i.ibb.co/9mGJYWp9/x.jpg",
    3: "https://i.ibb.co/Pz6h5Wq7/x.jpg",
    4: "https://i.ibb.co/sfmzKYq/x.jpg",
    5: "https://i.ibb.co/XZ5XYx4r/x.jpg",
    6: "https://i.ibb.co/FbVHf8JG/x.jpg",
}

# ===== Start Command =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can start the game!")
        return

    if game_active:
        await update.message.reply_text("❌ A game is already active! Wait for it to finish.")
        return

    game_active = True
    players_collection.delete_many({})
    await update.message.reply_text(
        "🎲 Dice game started!\nUsers, pick your number (1-6) using /dice <number>"
    )

# ===== Dice Pick (Users) =====
async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active
    if not game_active:
        await update.message.reply_text("No active game! Wait for the owner to start.")
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

    if players_collection.find_one({"user_id": user_id}):
        await update.message.reply_text("❌ You already picked a number for this game!")
        return

    players_collection.insert_one({
        "user_id": user_id,
        "username": username,
        "chosen_number": number
    })

    await update.message.reply_text(f"{username} picked {number}")

# ===== Owner DM Command to Set Result =====
async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global fixed_dice_roll
    if update.message.chat.type != "private":
        return
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
    await update.message.reply_text(f"✅ Dice result set to {fixed_dice_roll} for current game")

# ===== Group Result Command (Dice image + winners/losers) =====
async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active, fixed_dice_roll

    if update.message.chat.type == "private":
        return
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("❌ Only owner can announce the result!")
        return

    if not game_active:
        await update.message.reply_text("No active game!")
        return

    if not fixed_dice_roll:
        await update.message.reply_text("⚠️ No dice result set yet in DM!")
        return

    # ✅ Send fixed dice image from URL
    image_url = dice_images.get(fixed_dice_roll)
    if image_url:
        await context.bot.send_photo(update.effective_chat.id, photo=image_url)

    await asyncio.sleep(2)  # Optional wait for visual effect

    # Winners / Losers
    players = list(players_collection.find({}))
    winners = [p["username"] for p in players if p["chosen_number"] == fixed_dice_roll]
    losers = [p["username"] for p in players if p["chosen_number"] != fixed_dice_roll]

    result_msg = f"🎲 Dice rolled: {fixed_dice_roll}\n\n"
    result_msg += "🏆 Winners:\n" + ("\n".join(winners) if winners else "None") + "\n\n"
    result_msg += "❌ Losers:\n" + ("\n".join(losers) if losers else "None")

    await update.message.reply_text(result_msg)

    # Reset game
    game_active = False
    players_collection.delete_many({})
    fixed_dice_roll = None

# ===== Main =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

# DM handler
app.add_handler(CommandHandler(
    "result",
    set_result,
    filters=(filters.ChatType.PRIVATE & filters.User(user_id=OWNER_ID))
))
# Group handler
app.add_handler(CommandHandler(
    "result",
    show_result,
    filters=(filters.ChatType.GROUP & filters.User(user_id=OWNER_ID))
))

# Other handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dice", dice))

print("Bot is running...")
app.run_polling()
