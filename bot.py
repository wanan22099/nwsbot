import os
import json
import logging
import asyncio
import socket
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# ===== 初始化配置 =====
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WEBHOOK_URL = os.getenv("RAILWAY_WEBHOOK_URL")  # 必须包含 https://

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== 工具函数 =====
def get_abs_path(relative_path):
    return os.path.join(os.getcwd(), relative_path)

def load_config(file):
    try:
        with open(get_abs_path(f"config/{file}"), encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise

# ===== 业务逻辑 =====
async def send_scheduled_message():
    try:
        config = load_config("schedule.json")
        bot = Bot(token=TOKEN)
        with open(get_abs_path(f"assets/{config['image']}"), "rb") as photo:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=config['text'],
                parse_mode="MarkdownV2"
            )
    except Exception as e:
        logger.error(f"定时消息失败: {e}")

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        if not user.is_bot:
            try:
                welcome_msg = load_config("welcome/en.json")
                with open(get_abs_path(f"assets/{welcome_msg['image']}"), "rb") as photo:
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=photo,
                        caption=welcome_msg['text'],
                        parse_mode="MarkdownV2"
                    )
            except Exception as e:
                logger.error(f"欢迎消息失败: {e}")

# ===== Webhook 配置 =====
async def setup_webhook(app: Application, max_retries=3):
    for attempt in range(max_retries):
        try:
            if not WEBHOOK_URL.startswith('https://'):
                raise ValueError("WEBHOOK_URL 必须以 https:// 开头")
            
            # 测试域名解析
            host = WEBHOOK_URL.split('//')[1].split('/')[0]
            socket.gethostbyname(host)
            
            await app.bot.set_webhook(
                url=f"{WEBHOOK_URL}/telegram",
                drop_pending_updates=True,
                max_connections=50
            )
            logger.info(f"Webhook设置成功: {WEBHOOK_URL}/telegram")
            return
        except Exception as e:
            wait_time = (attempt + 1) * 5
            logger.warning(f"尝试 {attempt + 1}/{max_retries} 失败: {e}. {wait_time}秒后重试...")
            await asyncio.sleep(wait_time)
    raise RuntimeError("Webhook设置失败")

# ===== 主程序 =====
async def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    
    # 启动定时任务
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_scheduled_message, 'interval', minutes=1)
    scheduler.start()
    
    # 设置Webhook
    await setup_webhook(application)
    
    # 启动服务
    PORT = int(os.getenv("PORT", 8000))
    await application.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram"
    )
    
    logger.info("Bot 已启动")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"启动失败: {e}")
        raise
