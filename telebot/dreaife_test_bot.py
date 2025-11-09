from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入AI插件管理器
from ai_plugins.ai_manager import AIManager

# 加载环境变量
load_dotenv()

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='Telegram Bot 服务')
    parser.add_argument('--bot-name', type=str, default='dreaife_test_bot',
                        help='Bot 名称，用于日志和数据目录 (默认: dreaife_test_bot)')
    parser.add_argument('--log-dir', type=str, default=None,
                        help='日志目录路径 (默认: /logs/bot/<bot-name>/)')
    parser.add_argument('--data-dir', type=str, default=None,
                        help='数据目录路径 (默认: /data/bot/<bot-name>/)')
    return parser.parse_args()

def setup_logging(bot_name, log_dir=None):
    """
    设置日志配置
    :param bot_name: Bot 名称
    :param log_dir: 自定义日志目录，如果为 None 则使用默认路径
    """
    # 如果未指定日志目录，使用系统级默认路径 /logs/bot/<bot_name>
    if log_dir is None:
        log_dir = Path("/logs") / "bot" / bot_name
    else:
        log_dir = Path(log_dir)
    
    # 创建日志目录（如果不存在）
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置日志文件名
    log_file = log_dir / "telebot.log"

    # 创建 TimedRotatingFileHandler，每天滚动一次，最多保留 30 天的日志
    handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",     # 每天午夜滚动
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    # 配置文件后缀名，滚动后的文件格式将为 telebot.log.YYYY-MM-DD
    handler.suffix = "%Y-%m-%d"

    # 设置日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    handler.setFormatter(formatter)

    # 获取全局日志记录器，并添加 handler
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 根据需求也可以选择 DEBUG
    
    # 清除已有的 handlers，避免重复
    logger.handlers.clear()
    logger.addHandler(handler)
    
    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"日志目录: {log_dir}")
    logger.info(f"日志文件: {log_file}")
    
    return logger

def setup_data_dir(bot_name, data_dir=None):
    """
    设置数据目录
    :param bot_name: Bot 名称
    :param data_dir: 自定义数据目录，如果为 None 则使用默认路径
    :return: 数据目录路径
    """
    # 如果未指定数据目录，使用系统级默认路径 /data/bot/<bot_name>
    if data_dir is None:
        data_dir = Path("/data") / "bot" / bot_name
    else:
        data_dir = Path(data_dir)
    
    # 创建数据目录（如果不存在）
    data_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir

# 解析命令行参数
args = parse_args()

# 设置日志配置
logger = setup_logging(args.bot_name, args.log_dir)

# 设置数据目录
data_dir = setup_data_dir(args.bot_name, args.data_dir)
logger.info(f"数据目录: {data_dir}")

# 从环境变量读取 Telegram Bot Token
TOKEN = os.getenv('TELEGRAM_BOT_DREAIFE_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_BOT_DREAIFE_TOKEN 未设置在环境变量中")
    raise ValueError("请在 .env 文件中设置 TELEGRAM_BOT_DREAIFE_TOKEN")

# 创建AI管理器实例
ai_manager = AIManager()

# 定义处理 /start 命令的回调函数
async def start(update, context):
    logger.info("Start command received")
    await update.message.reply_text("你好！我是AI助手机器人。请发送消息与我聊天。")

# 定义处理文本消息的回调函数 - 修改为使用AI聊天
async def chat(update, context):
    user_id = str(update.effective_user.id)
    message = update.message.text
    
    logger.info(f"用户 {user_id} 发送消息: {message}")
    
    try:
        # 发送"正在思考..."的临时消息
        thinking_message = await update.message.reply_text("正在思考...")
        
        # 调用AI服务获取回复
        response = ai_manager.chat(user_id, message)
        
        # 更新临时消息为实际回复
        await thinking_message.edit_text(response)
        
        logger.info(f"AI回复给用户 {user_id}: {response[:50]}...")  # 只记录回复的前50个字符
    except Exception as e:
        error_message = f"处理消息时出错: {str(e)}"
        logger.error(error_message)
        await update.message.reply_text("抱歉，处理您的消息时出现了问题。请稍后再试。")

# 处理 /clear 命令，清除用户的聊天历史
async def clear_history(update, context):
    user_id = str(update.effective_user.id)
    ai_manager.clear_history(user_id)
    logger.info(f"已清除用户 {user_id} 的聊天历史")
    await update.message.reply_text("已清除您的聊天历史。")

# 处理 /help 命令
async def help_command(update, context):
    logger.info("Help command received")
    help_text = (
        "可用命令：\n"
        "/start - 开始对话\n"
        "/help - 显示帮助信息\n"
        "/clear - 清除聊天历史\n\n"
        "直接发送消息与AI助手对话。"
    )
    await update.message.reply_text(help_text)

def main():
    # 使用 Application.builder() 构建应用程序
    assert TOKEN is not None, "TOKEN 不能为 None"
    application = Application.builder().token(TOKEN).build()

    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    # 启动机器人（轮询方式）
    application.run_polling()

if __name__ == '__main__':
    main()
