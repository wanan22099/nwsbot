import os
import json
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from datetime import datetime

# 初始化配置
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# 支持的语言列表
SUPPORTED_LANGS = ["ar", "en", "fr", "pt", "es"]

def load_config(file):
    """加载JSON配置文件"""
    with open(f"config/{file}", encoding='utf-8') as f:
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
    """发送定时英文消息到频道"""
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
        
        # 发送图文消息
        with open(f"assets/{config['image']}", "rb") as photo:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=f"{config['text']}\n\n{config.get('footer', '')}",
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
    except Exception as e:
        print(f"定时消息发送失败: {e}")

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
        
        # 构建按钮（与频道推送相同但使用本地化文本）
        buttons = [
            get_button("open_app", lang),
            get_button("invite", lang),
            get_button("customer_service", lang),
            get_button("join_channel", lang)
        ]
        keyboard = [buttons[:2], buttons[2:]]
        
        # RTL语言处理（阿拉伯文）
        text = welcome_config["text"].format(name=user.first_name)
        if welcome_config.get("rtl", False):
            text = "\u202B" + text  # Unicode RTL控制字符
        
        # 发送私聊消息
        with open(f"assets/{welcome_config['image']}", "rb") as photo:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=photo,
                caption=text,
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )

if __name__ == "__main__":
    # 初始化定时任务
    scheduler = AsyncIOScheduler()
    schedule_config = load_config("schedule.json")
    scheduler.add_job(
        send_scheduled_message,
        trigger="interval",
        minutes=schedule_config["interval_minutes"],
        timezone="UTC"
    )
    
    # 启动Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user))
    
    scheduler.start()
    print("Bot已启动，支持语言:", SUPPORTED_LANGS)
    app.run_polling()
