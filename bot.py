import os
import json
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from datetime import datetime
import logging
import asyncio

# 初始化日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化配置
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WEBHOOK_URL = os.getenv("RAILWAY_WEBHOOK_URL")  # Railway 提供的域名

# 支持的语言列表
SUPPORTED_LANGS = ["ar", "en", "fr", "pt", "es"]

def get_abs_path(file_path):
    """获取绝对路径（适配 Railway 的文件系统）"""
    return os.path.join(os.getcwd(), file_path)

def load_config(file):
    """加载JSON配置文件（适配 Railway 路径）"""
    config_path = get_abs_path(f"config/{file}")
    with open(config_path, encoding='utf-8') as f:
        return json.load(f)

def get_button(button_id, lang="en"):
    """获取本地化按钮配置"""
    buttons = load_config("buttons.json")
    btn = buttons[button_id]
    return {
        "text": btn["text"].get(lang, btn["text"]["en"]),
        "type": btn["type"],
        "url": btn["url"]
    }

def detect_language(user):
    """检测用户语言（优先使用Telegram语言设置）"""
    if user.language_code in SUPPORTED_LANGS:
        return user.language_code
    return "en"  # 默认英语

async def send_scheduled_message():
    """发送定时消息到频道"""
    try:
        config = load_config("schedule.json")
        bot = Bot(token=TOKEN)
        
        # 构建2x2按钮布局
        buttons = [
            get_button("open_app", "en"),
            get_button("invite", "en"),
            get_button("customer_service", "en"),
            get_button("join_channel", "en")
        ]
        keyboard = [buttons[:2], buttons[2:]]
        
        # 发送图文消息（使用绝对路径）
        image_path = get_abs_path(f"assets/{config['image']}")
        with open(image_path, "rb") as photo:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=f"{config['text']}\n\n{config.get('footer', '')}",
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        logger.info("定时消息发送成功")
    except Exception as e:
        logger.error(f"定时消息发送失败: {e}")

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送多语言私聊欢迎"""
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        
        lang = detect_language(user)
        try:
            welcome_config = load_config(f"welcome/{lang}.json")
        except FileNotFoundError:
            welcome_config = load_config("welcome/en.json")
        
        # 构建按钮
        buttons = [
            get_button("open_app", lang),
            get_button("invite", lang),
            get_button("customer_service", lang),
            get_button("join_channel", lang)
        ]
        keyboard = [buttons[:2], buttons[2:]]
        
        # RTL语言处理
        text = welcome_config["text"].format(name=user.first_name)
        if welcome_config.get("rtl", False):
            text = "\u202B" + text
        
        # 发送私聊消息（使用绝对路径）
        image_path = get_abs_path(f"assets/{welcome_config['image']}")
        try:
            with open(image_path, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=photo,
                    caption=text,
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
            logger.info(f"欢迎消息发送给 {user.first_name} (语言: {lang})")
        except Exception as e:
            logger.error(f"欢迎消息发送失败: {e}")

async def on_startup(app):
    """启动时设置Webhook和定时任务"""
    try:
        # 设置Webhook
        await app.bot.set_webhook(f"{WEBHOOK_URL}/telegram")
        logger.info(f"Webhook 已设置: {WEBHOOK_URL}/telegram")
        
        # 启动定时任务
        scheduler = AsyncIOScheduler()
        schedule_config = load_config("schedule.json")
        scheduler.add_job(
            send_scheduled_message,
            trigger="interval",
            minutes=schedule_config["interval_minutes"],
            timezone="UTC"
        )
        scheduler.start()
        logger.info("定时任务已启动")
    except Exception as e:
        logger.critical(f"启动失败: {e}")
        raise

if __name__ == "__main__":
    # 初始化Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    
    # 适配Railway的Webhook模式
    PORT = int(os.environ.get("PORT", 8000))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram",
        startup=on_startup,
        secret_token="YOUR_WEBHOOK_SECRET"  # 可选：增强安全性
    )
