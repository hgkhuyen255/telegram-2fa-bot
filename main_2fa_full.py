
import os, pyotp, json, re
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

secrets = {}
if os.path.exists("secrets.json"):
    with open("secrets.json", "r") as f:
        secrets = json.load(f)

def save_secrets():
    with open("secrets.json", "w") as f:
        json.dump(secrets, f)

# Ghi nhớ user nào đang chờ secret
pending_add = {}

def is_base32_secret(text):
    return re.fullmatch(r"[A-Z2-7]{10,}", text.replace(" ", "").upper()) is not None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Gửi email để nhận mã 2FA. Dùng /add, /edit, /delete.")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) == 2:
            email, secret = context.args
            secrets[email] = secret
            save_secrets()
            await update.message.reply_text("✅ Đã thêm thành công.")
        elif len(context.args) == 1:
            email = context.args[0]
            pending_add[update.effective_user.id] = email
            await update.message.reply_text("📩 Gửi mã secret ở dòng tiếp theo để hoàn tất.")
        else:
            await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /add email secret")
    except:
        await update.message.reply_text("⚠️ Lỗi khi thêm.")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email, new_secret = context.args[0], context.args[1]
        if email in secrets:
            secrets[email] = new_secret
            save_secrets()
            await update.message.reply_text("✏️ Đã sửa thành công.")
        else:
            await update.message.reply_text("⚠️ Email chưa tồn tại.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /edit email secret")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email = context.args[0]
        if email in secrets:
            del secrets[email]
            save_secrets()
            await update.message.reply_text("🗑️ Đã xoá thành công.")
        else:
            await update.message.reply_text("⚠️ Email không tồn tại.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /delete email")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Nếu đang chờ mã secret
    if user_id in pending_add:
        email = pending_add.pop(user_id)
        if is_base32_secret(text.upper()):
            secrets[email] = text.strip()
            save_secrets()
            await update.message.reply_text("✅ Đã lưu mã 2FA.")
        else:
            await update.message.reply_text("❌ Mã không hợp lệ. Hãy thử lại với chuỗi Base32.")
        return

    # Nếu là email để lấy mã
    if text in secrets:
        try:
            code = pyotp.TOTP(secrets[text]).now()
            await update.message.reply_text(f"🔐 Mã 2FA: `{code}`", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ Lỗi khi tạo mã.")
    else:
        await update.message.reply_text("❌ Không tìm thấy email trong hệ thống.")

# Setup bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("edit", edit))
application.add_handler(CommandHandler("delete", delete))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL")
    await application.initialize()
    await application.bot.set_webhook(webhook_url)

@app.post("/")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
