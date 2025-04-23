import os
import yaml
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# 配置日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_config()
        return cls._instance
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open('config/settings.yaml', 'r') as f:
                self.settings = yaml.safe_load(f)
            with open('config/messages.yaml', 'r', encoding='utf-8') as f:
                self.messages = yaml.safe_load(f)
            
            # 环境变量覆盖配置
            self.settings['bot_token'] = os.getenv('BOT_TOKEN', self.settings.get('bot_token', ''))
            self.settings['channel_id'] = os.getenv('CHANNEL_ID', self.settings.get('channel_id', ''))
            self.settings['admin_id'] = int(os.getenv('ADMIN_ID', self.settings.get('admin_id', 0)))
            
            logger.info("配置加载成功")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise

class TelegramBot:
    def __init__(self):
        self.config = ConfigManager()
        self.scheduler = AsyncIOScheduler()
        self.application = None
        self.setup()

    def setup(self):
        """初始化设置"""
        self.setup_application()
        self.setup_handlers()
        self.setup_scheduler()

    def setup_application(self):
        """创建Telegram应用"""
        self.application = Application.builder() \
            .token(self.config.settings['bot_token']) \
            .build()

    def setup_handlers(self):
        """设置消息处理器"""
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.welcome_new_member)
        )
        self.application.add_handler(
            CommandHandler("start", self.cmd_start)
        )
        self.application.add_handler(
            CommandHandler("reload", self.cmd_reload)
        )
        self.application.add_error_handler(self.error_handler)

    def setup_scheduler(self):
        """设置定时任务"""
        hour, minute = map(int, self.config.settings['schedule']['daily_message']['time'].split(':'))
        self.scheduler.add_job(
            self.send_daily_message,
            CronTrigger(hour=hour, minute=minute)
        )
        self.scheduler.start()

    async def send_daily_message(self):
        """发送每日定时消息"""
        try:
            message = self.config.settings['schedule']['daily_message']['message']
            await self.application.bot.send_message(
                chat_id=self.config.settings['channel_id'],
                text=message
            )
            logger.info("每日消息发送成功")
        except Exception as e:
            logger.error(f"发送每日消息失败: {e}")

    async def welcome_new_member(self, update: Update, context: CallbackContext):
        """欢迎新成员"""
        try:
            for member in update.message.new_chat_members:
                if member.id == context.bot.id:
                    continue
                
                # 语言检测
                user_lang = member.language_code or 'en'
                lang = user_lang if user_lang in self.config.messages['welcome_messages'] else 'en'
                welcome = self.config.messages['welcome_messages'][lang]
                
                # 创建按钮
                keyboard = []
                for btn in welcome['buttons']:
                    if btn[1] == "app":
                        url = self.config.settings['app_link']
                    elif btn[1] == "channel":
                        url = self.config.settings['private_channel_link']
                    elif btn[1] == "support":
                        url = self.config.settings['support_link']
                    elif btn[1] == "invite":
                        url = f"https://t.me/share/url?url={self.config.settings['channel_id']}"
                    
                    keyboard.append([InlineKeyboardButton(btn[0], url=url)])
                
                # 发送欢迎消息
                with open('data/welcome_image.jpg', 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=member.id,
                        photo=photo,
                        caption=welcome['text'].format(username=member.first_name),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                logger.info(f"已欢迎新用户: {member.id}")
        except Exception as e:
            logger.error(f"欢迎新用户失败: {e}")

    async def cmd_start(self, update: Update, context: CallbackContext):
        """处理/start命令"""
        await update.message.reply_text("Bot已启动！")

    async def cmd_reload(self, update: Update, context: CallbackContext):
        """重新加载配置"""
        if update.effective_user.id == self.config.settings['admin_id']:
            self.config.load_config()
            await update.message.reply_text("配置已重新加载！")
        else:
            await update.message.reply_text("无权限执行此操作")

    async def error_handler(self, update: Update, context: CallbackContext):
        """错误处理"""
        logger.error(f"更新 {update} 导致错误: {context.error}")
        if update.effective_message:
            await update.effective_message.reply_text("出错了，请稍后再试")

    async def set_webhook(self):
        """设置Webhook"""
        webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook"
        await self.application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook设置为: {webhook_url}")

    def run(self):
        """启动Bot"""
        if os.getenv('RAILWAY_ENVIRONMENT'):
            # Railway生产环境使用Webhook
            port = int(os.getenv("PORT", 8443))
            self.application.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=None,
                secret_token=os.getenv('WEBHOOK_SECRET')
            )
        else:
            # 本地开发使用polling
            self.application.run_polling()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
