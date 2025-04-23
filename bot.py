import os
import json
from telegram import Bot, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# 加载配置
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

def load_content():
    with open("config/content.json") as f:
        content = json.load(f)
    with open("config/buttons.json") as f:
        buttons = json.load(f)
    return content, buttons

async def send_promo():
    """发送完整促销消息"""
    content, buttons = load_content()
    bot = Bot(token=TOKEN)
    
    try:
        # 1. 构建底部键盘
        keyboard = [
            [
                KeyboardButton(
                    text=btn["text"],
                    web_app=WebAppInfo(url=btn["data"]) if btn["type"] == "web_app" else None,
                    url=btn["data"] if btn["type"] == "url" else None
                ) for btn in row
            ] for row in [buttons["row1"], buttons["row2"]]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        # 2. 发送图片+文字
        with open(f"assets/{content['image']}", "rb") as photo:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=f"{content['text']}\n\n{content['footer']}",
                parse_mode="MarkdownV2",
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"发送失败: {e}")

if __name__ == "__main__":
    # 定时任务（每6小时）
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_promo,
        trigger="interval",
        hours=6,
        timezone="Asia/Shanghai"
    )
    
    scheduler.start()
    print("定时推送已启动...")
    while True: pass  # 保持进程运行
