import os
import sys
import json
import logging
import asyncio
import socket
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==== 1. 环境验证 ====
def validate_env():
    required_vars = {
        "BOT_TOKEN": os.getenv("BOT_TOKEN"),
        "CHANNEL_ID": os.getenv("CHANNEL_ID"),
        "RAILWAY_WEBHOOK_URL": os.getenv("RAILWAY_WEBHOOK_URL")
    }
    
    # 调试输出
    print("=== 环境变量 ===")
    for name, value in required_vars.items():
        print(f"{name}: {'*****' if 'TOKEN' in name else value}")
    
    if missing := [name for name, val in required_vars.items() if not val]:
        raise ValueError(f"缺少环境变量: {missing}")
    
    if not required_vars["RAILWAY_WEBHOOK_URL"].startswith("https://"):
        raise ValueError("WEBHOOK_URL 必须以 https:// 开头")
    
    return required_vars

# ==== 2. 初始化 ====
try:
    env = validate_env()
    TOKEN = env["BOT_TOKEN"]
    CHANNEL_ID = env["CHANNEL_ID"]
    WEBHOOK_URL = env["RAILWAY_WEBHOOK_URL"].rstrip("/")
except Exception as e:
    logging.critical(f"初始化失败: {str(e)}")
    sys.exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==== 3. 业务逻辑 ====
async def send_scheduled_message():
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(CHANNEL_ID, "定时消息测试")
    except Exception as e:
        logger.error(f"定时消息失败: {str(e)}")

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("欢迎！")
    except Exception as e:
        logger.error(f"欢迎失败: {str(e)}")

# ==== 4. 主程序 ====
async def main():
    # 创建应用
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, welcome_user))
    
    # 定时任务
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_scheduled_message, 'interval', minutes=1)
    scheduler.start()
    
    # Webhook配置
    await application.bot.set_webhook(
        url=f"{WEBHOOK_URL}/telegram",
        drop_pending_updates=True
    )
    
    # 启动服务
    PORT = int(os.getenv("PORT", 8000))
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram"
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"启动失败: {str(e)}")
        sys.exit(1)
