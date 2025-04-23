import os
import time
import logging
from datetime import datetime
from threading import Thread

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext, 
    CallbackQueryHandler
)
from telegram.error import TelegramError
import redis
from apscheduler.schedulers.background import BackgroundScheduler

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.bot = Bot(token=token)
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # 初始化Redis
        redis_url = os.getenv('REDIS_URL') or \
                   f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}"
        self.redis = redis.from_url(redis_url)
        
        # 初始化定时任务调度器
        self.scheduler = BackgroundScheduler()
        self._setup_scheduler()
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self):
        """注册所有消息处理器"""
        # 新成员加入处理
        self.dispatcher.add_handler(
            MessageHandler(Filters.status_update.new_chat_members, self.welcome_new_member)
        )
        
        # 按钮回调处理
        self.dispatcher.add_handler(
            CallbackQueryHandler(self.button_callback)
        )
        
        # 测试命令
        self.dispatcher.add_handler(
            CommandHandler('test', self.test_command)
        )
        
        # 设置定时任务命令
        self.dispatcher.add_handler(
            CommandHandler('set_schedule', self.set_schedule)
        )
    
    def _setup_scheduler(self):
        """配置定时任务调度器"""
        self.scheduler.add_job(
            self.check_scheduled_posts,
            'interval',
            minutes=1,
            id='post_checker'
        )
        self.scheduler.start()
    
    def check_scheduled_posts(self):
        """检查并发送定时消息"""
        try:
            now = datetime.now().strftime('%H:%M')
            scheduled_posts = self.redis.hgetall('scheduled_posts')
            
            for channel_id, post_time in scheduled_posts.items():
                if post_time.decode('utf-8') == now:
                    self.send_scheduled_message(channel_id.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")
    
    def welcome_new_member(self, update: Update, context: CallbackContext):
        """新成员加入处理"""
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
                
            try:
                self.send_welcome_message(update.effective_chat.id, member.id)
            except TelegramError as e:
                logger.error(f"Error sending welcome message: {e}")
    
    def send_welcome_message(self, chat_id, user_id):
        """发送欢迎消息"""
        photo_url = os.getenv('WELCOME_IMAGE_URL', 'https://example.com/welcome.jpg')
        
        welcome_text = """
        Welcome to our channel! 🎉

        Here you'll find regular updates and interesting content.
        Feel free to explore the options below:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("Open App", callback_data='open_app'),
                InlineKeyboardButton("Private Channel", callback_data='private_channel')
            ],
            [
                InlineKeyboardButton("Contact Support", callback_data='contact_support'),
                InlineKeyboardButton("Invite Friends", callback_data='invite_friends')
            ]
        ]
        
        self.bot.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def send_scheduled_message(self, channel_id):
        """发送定时消息"""
        photo_url = os.getenv('SCHEDULED_IMAGE_URL', 'https://example.com/scheduled.jpg')
        
        message_text = """
        Daily Update 🌟

        Here's your regular update with the latest news and content.
        Check out the options below:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("Open App", callback_data='open_app'),
                InlineKeyboardButton("Private Channel", callback_data='private_channel')
            ],
            [
                InlineKeyboardButton("Contact Support", callback_data='contact_support'),
                InlineKeyboardButton("Invite Friends", callback_data='invite_friends')
            ]
        ]
        
        try:
            self.bot.send_photo(
                chat_id=channel_id,
                photo=photo_url,
                caption=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
        except TelegramError as e:
            logger.error(f"Error sending scheduled message: {e}")
    
    def button_callback(self, update: Update, context: CallbackContext):
        """按钮回调处理"""
        query = update.callback_query
        query.answer()
        
        data = query.data
        chat_id = query.message.chat_id
        
        if data == 'open_app':
            app_url = os.getenv('APP_URL', 'https://t.me/your_app')
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Please click here to open the app: {app_url}"
            )
        
        elif data == 'private_channel':
            channel_link = os.getenv('PRIVATE_CHANNEL_LINK', 'https://t.me/your_private_channel')
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Join our private channel here: {channel_link}"
            )
        
        elif data == 'contact_support':
            support_link = os.getenv('SUPPORT_LINK', 'https://t.me/your_support')
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Contact our support team here: {support_link}"
            )
        
        elif data == 'invite_friends':
            invite_link = os.getenv('INVITE_LINK', 'https://t.me/your_channel')
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Invite your friends to join us! Share this link: {invite_link}"
            )
    
    def set_schedule(self, update: Update, context: CallbackContext):
        """设置定时任务命令"""
        if len(context.args) != 2:
            update.message.reply_text("Usage: /set_schedule <channel_id> <HH:MM>")
            return
        
        channel_id, schedule_time = context.args
        try:
            self.redis.hset('scheduled_posts', channel_id, schedule_time)
            update.message.reply_text(
                f"Schedule set successfully!\n"
                f"Channel: {channel_id}\n"
                f"Time: {schedule_time} UTC"
            )
        except Exception as e:
            update.message.reply_text(f"Error setting schedule: {e}")
    
    def test_command(self, update: Update, context: CallbackContext):
        """测试命令"""
        update.message.reply_text("Bot is working!")
    
    def run(self):
        """启动机器人"""
        self.updater.start_polling()
        self.updater.idle()

def main():
    # 从环境变量获取Token
    token = os.getenv('TELEGRAM_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError(
            "TELEGRAM_TOKEN environment variable not set. "
            "Please set it in Railway Variables or .env file"
        )
    
    # 创建并运行机器人
    bot = TelegramBot(token)
    logger.info("Bot started successfully")
    bot.run()

if __name__ == '__main__':
    main()
