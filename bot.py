import os
import yaml
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 加载配置
def load_config():
    with open('config/settings.yaml', 'r') as f:
        settings = yaml.safe_load(f)
    with open('config/messages.yaml', 'r', encoding='utf-8') as f:
        messages = yaml.safe_load(f)
    return settings, messages

# 从环境变量覆盖配置
def get_config():
    settings, messages = load_config()
    
    # 环境变量优先
    if os.getenv('BOT_TOKEN'):
        settings['bot_token'] = os.getenv('BOT_TOKEN')
    if os.getenv('CHANNEL_ID'):
        settings['channel_id'] = os.getenv('CHANNEL_ID')
    if os.getenv('ADMIN_ID'):
        settings['admin_id'] = int(os.getenv('ADMIN_ID'))
    if os.getenv('SUPPORT_LINK'):
        settings['support_link'] = os.getenv('SUPPORT_LINK')
    if os.getenv('PRIVATE_CHANNEL_LINK'):
        settings['private_channel_link'] = os.getenv('PRIVATE_CHANNEL_LINK')
    if os.getenv('APP_LINK'):
        settings['app_link'] = os.getenv('APP_LINK')
    
    return settings, messages

settings, messages = get_config()

async def send_daily_message():
    """定时发送每日消息到频道"""
    try:
        message = settings['schedule']['daily_message']['message']
        await application.bot.send_message(
            chat_id=settings['channel_id'], 
            text=message
        )
        logger.info("Daily message sent successfully")
    except Exception as e:
        logger.error(f"Error sending daily message: {e}")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """欢迎新成员"""
    try:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                continue
            
            # 简化版语言检测 - 实际应根据用户设置或IP判断
            user_language = detect_user_language(member)
            
            welcome_msg = messages['welcome_messages'].get(
                user_language,
                messages['welcome_messages']['en']  # 默认英语
            )
            
            keyboard = []
            for btn_text, btn_data in welcome_msg['buttons']:
                if btn_data == "app":
                    url = settings['app_link']
                elif btn_data == "channel":
                    url = settings['private_channel_link']
                elif btn_data == "support":
                    url = settings['support_link']
                elif btn_data == "invite":
                    url = f"https://t.me/share/url?url={settings['channel_id']}"
                
                keyboard.append([InlineKeyboardButton(btn_text, url=url)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 发送欢迎消息
            with open('data/welcome_image.jpg', 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=member.id,
                    photo=photo,
                    caption=welcome_msg['text'],
                    reply_markup=reply_markup
                )
            logger.info(f"Welcome message sent to {member.id}")
    except Exception as e:
        logger.error(f"Error in welcome_new_member: {e}")

def detect_user_language(user):
    """简化版语言检测"""
    # 这里可以根据user.language_code或更复杂的逻辑实现
    # 现在返回默认英语
    return 'en'

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """重新加载配置（管理员命令）"""
    if update.effective_user.id == settings['admin_id']:
        global settings, messages
        settings, messages = get_config()
        await update.message.reply_text("Configuration reloaded successfully!")
        logger.info("Configuration reloaded by admin")
    else:
        await update.message.reply_text("You are not authorized to perform this action.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/start命令"""
    await update.message.reply_text("Hello! I'm your bot. I welcome new members and send daily messages.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理错误"""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again later.")

# 创建Application
application = Application.builder().token(settings['bot_token']).build()

def setup_handlers():
    """设置处理器"""
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CommandHandler("reload", reload_config))
    application.add_handler(CommandHandler("start", start))
    application.add_error_handler(error_handler)

def setup_scheduler():
    """设置定时任务"""
    scheduler = AsyncIOScheduler()
    # 从配置获取时间，格式"HH:MM"
    hour, minute = map(int, settings['schedule']['daily_message']['time'].split(':'))
    trigger = CronTrigger(hour=hour, minute=minute)
    scheduler.add_job(send_daily_message, trigger)
    scheduler.start()

async def set_webhook():
    """设置Webhook"""
    webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

async def startup():
    """启动时运行"""
    await set_webhook()
    setup_scheduler()
    logger.info("Bot started with webhook")

def main():
    """启动应用"""
    setup_handlers()
    
    port = int(os.getenv("PORT", 8443))
    
    # 在Railway上运行时使用Webhook，本地开发使用polling
    if os.getenv('RAILWAY_ENVIRONMENT'):
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=None,  # 已经在startup中设置
            secret_token=os.getenv('WEBHOOK_SECRET', 'your-secret-token'),
        )
    else:
        application.run_polling()

if __name__ == '__main__':
    application.run_polling()  # 本地开发用polling
