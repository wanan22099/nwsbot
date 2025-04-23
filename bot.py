import os
import logging
from datetime import datetime, time
from threading import Thread
from queue import Queue

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

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化Redis
r = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None),
    db=0
)

# 消息队列
message_queue = Queue()

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.bot = Bot(token=token)
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # 注册处理器
        self._register_handlers()
        
        # 启动定时任务线程
        self._start_scheduler()
    
    def _register_handlers(self):
        # 新成员加入处理
        self.dispatcher.add_handler(
            MessageHandler(Filters.status_update.new_chat_members, self.welcome_new_member)
        
        # 按钮回调处理
        self.dispatcher.add_handler(
            CallbackQueryHandler(self.button_callback))
        
        # 测试命令
        self.dispatcher.add_handler(
            CommandHandler('test', self.test_command))
    
    def _start_scheduler(self):
        # 启动定时任务线程
        scheduler_thread = Thread(target=self._scheduler_worker)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    def _scheduler_worker(self):
        """定时任务工作线程"""
        while True:
            # 检查是否有定时任务需要执行
            now = datetime.now().strftime('%H:%M')
            scheduled_posts = r.hgetall('scheduled_posts')
            
            for channel_id, post_time in scheduled_posts.items():
                if post_time.decode('utf-8') == now:
                    self.send_scheduled_message(channel_id.decode('utf-8'))
            
            # 每分钟检查一次
            time.sleep(60)
    
    def welcome_new_member(self, update: Update, context: CallbackContext):
        """新成员加入处理"""
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
                
            try:
                # 发送欢迎消息
                self.send_welcome_message(update.effective_chat.id, member.id)
            except TelegramError as e:
                logger.error(f"Error sending welcome message: {e}")
    
    def send_welcome_message(self, chat_id, user_id):
        """发送欢迎消息"""
        # 图片URL或文件ID
        photo_url = "https://example.com/welcome_image.jpg"  # 替换为你的图片
        
        # 欢迎文本
        welcome_text = """
        Welcome to our channel! 🎉

        Here you'll find regular updates and interesting content.
        Feel free to explore the options below:
        """
        
        # 创建按钮
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
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 发送带图片和按钮的消息
        self.bot.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )
    
    def send_scheduled_message(self, channel_id):
        """发送定时消息"""
        # 图片URL或文件ID
        photo_url = "https://example.com/scheduled_image.jpg"  # 替换为你的图片
        
        # 消息文本
        message_text = """
        Daily Update 🌟

        Here's your regular update with the latest news and content.
        Check out the options below:
        """
        
        # 创建按钮
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
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 发送消息
        try:
            self.bot.send_photo(
                chat_id=channel_id,
                photo=photo_url,
                caption=message_text,
                reply_markup=reply_markup
            )
        except TelegramError as e:
            logger.error(f"Error sending scheduled message: {e}")
    
    def button_callback(self, update: Update, context: CallbackContext):
        """按钮回调处理"""
        query = update.callback_query
        query.answer()
        
        data = query.data
        chat_id = query.message.chat_id
        
        if data == 'open_app':
            # 打开内置APP
            app_url = "https://telegram.me/your_app"  # 替换为你的APP链接
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Please click here to open the app: {app_url}"
            )
        
        elif data == 'private_channel':
            # 添加私有频道
            channel_link = "https://t.me/your_private_channel"  # 替换为你的频道链接
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Join our private channel here: {channel_link}"
            )
        
        elif data == 'contact_support':
            # 联系客服
            support_link = "https://t.me/your_support"  # 替换为你的客服链接
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Contact our support team here: {support_link}"
            )
        
        elif data == 'invite_friends':
            # 邀请朋友
            invite_link = "https://t.me/your_channel"  # 替换为你的频道邀请链接
            self.bot.send_message(
                chat_id=chat_id,
                text=f"Invite your friends to join us! Share this link: {invite_link}"
            )
    
    def test_command(self, update: Update, context: CallbackContext):
        """测试命令"""
        update.message.reply_text("Bot is working!")
    
    def run(self):
        """启动机器人"""
        self.updater.start_polling()
        self.updater.idle()

def main():
    # 从环境变量获取Token
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_TOKEN environment variable not set")
    
    # 创建并运行机器人
    bot = TelegramBot(token)
    bot.run()

if __name__ == '__main__':
    main()
