import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, time

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
        bot = context.bot if hasattr(context, 'bot') else context
        text, reply_markup = await create_message()
        
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=IMAGE_URL,
            caption=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        logger.info("Scheduled message sent successfully")
    except Exception as e:
        logger.error(f"Error sending scheduled message: {e}")
        if ADMIN_CHAT_ID:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Error sending scheduled message: {e}")

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
        logger.error(f"Error in welcome: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """错误处理"""
    logger.error(msg="Exception:", exc_info=context.error)
    if ADMIN_CHAT_ID:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"An error occurred: {context.error}"
        )

def main():
    """启动机器人"""
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_error_handler(error_handler)
    
    # 设置定时任务（关键修改部分）
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_scheduled_message,
        'cron',
        hour=8,
        minute=0,
        args=[application.application_context()]  # 正确获取上下文的方式
    )
    scheduler.start()
    
    # 启动机器人
    application.run_polling()

if __name__ == '__main__':
    main()
