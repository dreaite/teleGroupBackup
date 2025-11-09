# Bot 服务管理文档（服务创建记录）

下面包含 systemd 服务单元示例、安装与启动步骤，以及如何把服务加入到系统服务并启动的具体命令。

---

## systemd 服务单元示例

我们在仓库中提供了一个模板文件：`deploy/telegram-bot.service`。

示例内容（针对 `dreaife_test_bot`）：

```ini
[Unit]
Description=Telegram Bot Service - dreaife_test_bot
After=network.target

[Service]
Type=simple
User=dreaife
WorkingDirectory=/home/dreaife/bot
# 在 ExecStartPre 中确保目录存在并且属于 dreaife 用户
ExecStartPre=/bin/mkdir -p /logs/bot/dreaife_test_bot
ExecStartPre=/bin/mkdir -p /data/bot/dreaife_test_bot
ExecStartPre=/bin/chown -R dreaife:dreaife /logs/bot/dreaife_test_bot /data/bot/dreaife_test_bot

# 使用项目的 venv Python 运行脚本，并显式指定日志和数据目录
ExecStart=/home/dreaife/bot/venv/bin/python /home/dreaife/bot/telebot/dreaife_test_bot.py --bot-name dreaife_test_bot --log-dir /logs/bot/dreaife_test_bot --data-dir /data/bot/dreaife_test_bot

Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## 安装并启动服务（步骤）

1. 将模板复制到 systemd 目录（需要 sudo 权限）

```bash
# 在仓库根目录下执行：
sudo cp deploy/telegram-bot.service /etc/systemd/system/dreaife_test_bot.service

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start dreaife_test_bot

# 查看状态
sudo systemctl status dreaife_test_bot

# 开机自启
sudo systemctl enable dreaife_test_bot
```

> 说明：模板中有 `ExecStartPre` 指令，会在服务启动前自动创建 `/logs/bot/dreaife_test_bot` 和 `/data/bot/dreaife_test_bot` 并设置拥有者为 `dreaife`（以确保服务有写权限）。

---

## 日志与数据位置（系统级默认）

- 日志：`/logs/bot/<bot_name>/telebot.log`（每天轮转，保留 30 天）
- 数据：`/data/bot/<bot_name>/`（用于持久化用户会话等数据）

如果你想更改这些路径，可以在 service 的 `ExecStart` 中传入 `--log-dir` 和 `--data-dir` 参数，或者直接修改 `deploy/telegram-bot.service` 中的路径。

---

## 在服务文件中使用 .env

当前代码使用 `python-dotenv` 在进程启动时加载仓库根目录下的 `.env`，因此确保 `~/bot/.env` 中包含：

```
TELEGRAM_BOT_DREAIFE_TOKEN="<your-telegram-token>"
OPENAI_API_KEY="<your-openai-key>"
```

注意：systemd 启动服务不会自动给进程暴露交互式 shell 环境。`python-dotenv` 在脚本导入时会尝试读取 `.env` 文件，所以把 `.env` 放在 `~/bot/.env` 即可被读取。

---

## 日志查看与维护

- 查看实时日志：

```bash
# Bot 自己的日志
sudo tail -f /logs/bot/dreaife_test_bot/telebot.log

# systemd 日志
sudo journalctl -u dreaife_test_bot -f
```

- 手动清理 30 天之前的日志（如果需要）：

```bash
sudo find /logs/bot/dreaife_test_bot/ -name "telebot.log.*" -mtime +30 -delete
```

---

## 启动测试（快速验证）

1. 在仓库根目录确保 venv 存在并已安装依赖：

```bash
cd /home/dreaife/bot
source venv/bin/activate
pip install -r requirements.txt
```

2. 临时以当前 shell 启动（不使用 systemd）方便调试：

```bash
# 指定路径测试（无需 sudo）
python telebot/dreaife_test_bot.py --bot-name dreaife_test_bot --log-dir /tmp/logs/testbot --data-dir /tmp/data/testbot
```

3. 安装到 systemd 并启动（需 sudo，参见上文）

---

## 服务创建记录

### 2025-11-10 - systemd 模板添加

- ✅ 在仓库 `deploy/telegram-bot.service` 中添加 systemd 单元模板
- ✅ 更新 `telebot/dreaife_test_bot.py`，默认使用 `/logs/bot/<bot_name>` 和 `/data/bot/<bot_name>`，支持通过 CLI 覆盖
- ✅ 在本文件记录安装与启动步骤

---

*最后更新: 2025-11-10*
