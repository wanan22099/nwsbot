import os
import time
import logging
from datetime import datetime
import pytz  # 新增导入
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
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)  # 设置时区
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
            timezone=pytz.UTC,  # 设置时区
            id='post_checker'
        )
        self.scheduler.start()
    
    def check_scheduled_posts(self):
        """检查并发送定时消息"""
        try:
            now = datetime.now(pytz.UTC).strftime('%H:%M')  # 使用时区
            scheduled_posts = self.redis.hgetall('scheduled_posts')
            
            for channel_id, post_time in scheduled_posts.items():
                if post_time.decode('utf-8') == now:
                    self.send_scheduled_message(channel_id.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")
    
    # ... (其余方法保持不变，与之前提供的代码相同) ...

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
