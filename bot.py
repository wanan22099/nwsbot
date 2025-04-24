import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 环境变量
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
PRIVATE_CHANNEL_LINK = os.getenv('PRIVATE_CHANNEL_LINK', 'https://t.me/yourprivatechannel')
CUSTOMER_SERVICE_LINK = os.getenv('CUSTOMER_SERVICE_LINK', 'https://t.me/yourservice')
APP_LINK = os.getenv('APP_LINK', 'https://t.me/yourapp')
IMAGE_URL = os.getenv('IMAGE_URL', 'https://example.com/image.jpg')

async def create_message():
    """创建消息内容和键盘"""
    text = """
    *Welcome to Our Channel!* 🌟

    Here you'll find the latest updates and news. 
    Feel free to explore our resources and join our community!
    """
    
    keyboard = [
        [
            InlineKeyboardButton("Open App", url=APP_LINK),
            InlineKeyboardButton("Private Channel", url=PRIVATE_CHANNEL_LINK)
        ],
        [
            InlineKeyboardButton("Customer Service", url=CUSTOMER_SERVICE_LINK),
            InlineKeyboardButton("Invite Friends", url="https://t.me/share/url?url=https://t.me/yourchannel")
        ]
    ]
    
    return text, InlineKeyboardMarkup(keyboard)

async def send_scheduled_message(context: ContextTypes.DEFAULT_TYPE):
    """定时发送消息到频道"""
    try:
        text, reply_markup = await create_message()
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=IMAGE_URL,
            caption=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info("定时消息发送成功")
    except Exception as e:
        logger.error(f"定时消息发送失败: {e}")
        if ADMIN_CHAT_ID:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"定时消息发送失败: {e}"
            )

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """欢迎新成员"""
    try:
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
                
            text, reply_markup = await create_message()
            await context.bot.send_photo(
                chat_id=member.id,
                photo=IMAGE_URL,
                caption=f"Hi {member.first_name}! 👋\n\n{text}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"欢迎消息发送失败: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """错误处理"""
    logger.error(msg="异常:", exc_info=context.error)
    if ADMIN_CHAT_ID:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"发生错误: {context.error}"
        )

def main():
    """启动机器人"""
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member)
    )
    application.add_error_handler(error_handler)
    
    # 设置定时任务（关键修正部分）
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_message,
        'cron',
        hour=8,
        minute=0,
        kwargs={'context': application.bot}  # 直接传递bot实例
    )
    scheduler.start()
    
    application.run_polling()

if __name__ == '__main__':
    main()
