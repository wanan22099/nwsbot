import os
import json
import logging
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# ===== 初始化配置 =====
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
WEBHOOK_URL = os.getenv("RAILWAY_WEBHOOK_URL")  # 格式: https://xxx.up.railway.app

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== 工具函数 =====
def get_abs_path(relative_path):
    """获取绝对路径（适配Railway容器环境）"""
    return os.path.join(os.getcwd(), relative_path)

def load_config(file):
    """加载JSON配置文件"""
    try:
        with open(get_abs_path(f"config/{file}"), encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise

# ===== 业务逻辑 =====
async def send_scheduled_message():
    """定时频道消息推送"""
    try:
        config = load_config("schedule.json")
        bot = Bot(token=TOKEN)
        
        with open(get_abs_path(f"assets/{config['image']}"), "rb") as photo:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=config['text'],
                parse_mode="MarkdownV2"
            )
        logger.info("定时消息发送成功")
    except Exception as e:
        logger.error(f"定时消息发送失败: {e}")

async def welcome_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """新成员欢迎处理"""
    for user in update.message.new_chat_members:
        if not user.is_bot:
            try:
                lang = 'en'  # 简化为英文示例
                welcome_msg = load_config(f"welcome/{lang}.json")
                
                with open(get_abs_path(f"assets/{welcome_msg['image']}"), "rb") as photo:
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=photo,
                        caption=welcome_msg['text'],
                        parse_mode="MarkdownV2"
                    )
                logger.info(f"已欢迎用户: {user.first_name}")
            except Exception as e:
                logger.error(f"欢迎消息发送失败: {e}")

# ===== 启动逻辑 =====
async def on_startup(app: Application):
    """启动时初始化"""
    try:
        # 设置Webhook
        await app.bot.set_webhook(
            url=f"{WEBHOOK_URL}/telegram",
            # secret_token=os.getenv("WEBHOOK_SECRET")  # 可选安全验证
        )
        logger.info(f"Webhook已设置: {WEBHOOK_URL}/telegram")
        
        # 启动定时任务
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            send_scheduled_message,
            'interval',
            minutes=load_config("schedule.json")["interval_minutes"],
            timezone="UTC"
        )
        scheduler.start()
        logger.info("定时任务已启动")
    except Exception as e:
        logger.critical(f"启动失败: {e}")
        raise

if __name__ == "__main__":
    # 创建Bot实例
    application = Application.builder().token(TOKEN).build()
    
    # 添加处理器
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_user)
    )
    
    # 启动Webhook服务（关键修改点）
    PORT = int(os.environ.get("PORT", 8000))
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{WEBHOOK_URL}/telegram",
        # 新版PTB需要通过post_init参数传递启动函数
        post_init=on_startup,
        drop_pending_updates=True
    )
