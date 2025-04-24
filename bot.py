import os
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import time, datetime

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量获取配置
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')  # 你的频道ID，如 @yourchannel
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')  # 管理员聊天ID，用于接收错误通知
PRIVATE_CHANNEL_LINK = os.getenv('PRIVATE_CHANNEL_LINK', 'https://t.me/yourprivatechannel')
CUSTOMER_SERVICE_LINK = os.getenv('CUSTOMER_SERVICE_LINK', 'https://t.me/yourservice')
APP_LINK = os.getenv('APP_LINK', 'https://t.me/yourapp')

# 图片URL或文件ID
IMAGE_URL = os.getenv('IMAGE_URL', 'https://example.com/image.jpg')

def create_message():
    """创建消息内容和键盘"""
    # 消息文本
    text = """
    *Welcome to Our Channel!* 🌟

    Here you'll find the latest updates and news. 
    Feel free to explore our resources and join our community!
    """
    
    # 创建内联键盘
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
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return text, reply_markup

def send_scheduled_message(context: CallbackContext):
    """定时发送消息到频道"""
    try:
        bot = context.bot
        text, reply_markup = create_message()
        
        # 发送带图片的消息
        bot.send_photo(
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
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Error sending scheduled message: {e}")

def welcome_new_member(update: Update, context: CallbackContext):
    """欢迎新成员"""
    try:
        for member in update.message.new_chat_members:
            if member.is_bot:  # 忽略其他机器人
                continue
                
            text, reply_markup = create_message()
            
            # 发送欢迎消息
            context.bot.send_photo(
                chat_id=member.id,
                photo=IMAGE_URL,
                caption=f"Hi {member.first_name}! 👋\n\n{text}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            logger.info(f"Welcome message sent to {member.first_name}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")
        if ADMIN_CHAT_ID:
            context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Error sending welcome message: {e}")

def error_handler(update: Update, context: CallbackContext):
    """错误处理"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if ADMIN_CHAT_ID:
        context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"An error occurred: {context.error}"
        )

def main():
    """启动机器人"""
    # 创建Updater并传递bot的token
    updater = Updater(TOKEN, use_context=True)
    
    # 获取dispatcher来注册处理器
    dp = updater.dispatcher
    
    # 添加处理器
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome_new_member))
    dp.add_error_handler(error_handler)
    
    # 设置定时任务
    scheduler = BackgroundScheduler()
    # 每天UTC时间8:00发送消息（可根据需要调整）
    scheduler.add_job(
        send_scheduled_message,
        'cron',
        hour=8,
        minute=0,
    )
    scheduler.start()
    
    # 启动机器人
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
