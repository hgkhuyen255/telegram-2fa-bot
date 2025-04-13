
import os
import pyotp
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
secrets = {}

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Gửi email để nhận mã 2FA. Dùng /add, /edit, /delete để quản lý.")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email, secret = context.args[0], context.args[1]
        secrets[email] = secret
        await update.message.reply_text("✅ Đã thêm thành công.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /add email secret")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email, new_secret = context.args[0], context.args[1]
        if email in secrets:
            secrets[email] = new_secret
            await update.message.reply_text("✏️ Đã chỉnh sửa thành công.")
        else:
            await update.message.reply_text("⚠️ Email chưa tồn tại.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /edit email new_secret")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        email = context.args[0]
        if email in secrets:
            del secrets[email]
            await update.message.reply_text("🗑️ Đã xoá thành công.")
        else:
            await update.message.reply_text("⚠️ Email không tồn tại.")
    except:
        await update.message.reply_text("⚠️ Sai cú pháp. Dùng: /delete email")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in secrets:
        code = pyotp.TOTP(secrets[text]).now()
        await update.message.reply_text(f"🔐 Mã 2FA: `{code}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("👋 Xin chào!")

# --- Setup bot app ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("edit", edit))
application.add_handler(CommandHandler("delete", delete))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL") + "/" + BOT_TOKEN
    await application.bot.set_webhook(webhook_url)

@app.post(f"/{BOT_TOKEN}")
async def webhook_handler(req: Request):
    data = await req.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return {"ok": True}
