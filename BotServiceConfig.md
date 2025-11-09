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

## 🚀 Git Hook 自动部署（推荐）

我们提供了 Git Hook 来实现**自动部署**：当你将 `dev` 分支合并到 `master` 时，自动检测并部署/重启服务在本地（Linux）。

### 安装 Git Hook

在仓库根目录运行：

```bash
# 安装 Git Hook
./deploy/install-hooks.sh
```

这会将 `deploy/post-merge` 复制到 `.git/hooks/post-merge` 并设置执行权限。

### 工作原理

当你执行 `git merge dev`（在 master 分支上）时，hook 会：

1. **自动扫描所有服务文件**
   - 扫描 `deploy/` 目录下所有 `.service` 文件
   - 根据文件名确定服务名（例如 `telegram-bot.service` → 服务名为 `telegram-bot`）

2. **逐个处理每个服务**
   - 如果服务已安装：停止 → 更新服务文件 → 重载配置 → 启动
   - 如果服务未安装：复制服务文件 → 启用开机自启 → 启动

3. **验证并汇总**
   - 检查每个服务是否成功启动
   - 统计成功/失败的服务数量
   - 显示失败服务的日志查看命令

### 使用示例

```bash
# 在 dev 分支开发
git checkout dev
# ... 做一些改动 ...
git add .
git commit -m "更新功能"

# 合并到 master 自动部署所有服务
git checkout master
git merge dev
# 👆 自动检测并部署 deploy/ 下的所有 .service 文件！
```

### 输出示例

```
=========================================
🤖 检测到 master 分支合并，准备部署服务...
=========================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 处理服务: telegram-bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 服务已存在，准备重启...
⏸️  停止服务: telegram-bot
📝 更新服务文件到 /etc/systemd/system/telegram-bot.service
🔄 重新加载 systemd 配置
▶️  启动服务: telegram-bot
✅ 服务重启成功！

=========================================
🎉 部署完成！
=========================================

📊 部署汇总:
   总服务数: 1
   成功: 1
   失败: 0

📊 查看所有服务状态:
   sudo systemctl status 'dreaife_*' --no-pager

📊 查看日志 (示例):
   应用日志: sudo tail -f /logs/bot/<service-name>/telebot.log
   系统日志: sudo journalctl -u <service-name> -f
```

### 多服务支持

如果你在 `deploy/` 目录下有多个服务文件：

```
deploy/
├── telegram-bot.service
├── discord-bot.service
└── webhook-server.service
```

合并时会自动处理所有服务：

```
📦 处理服务: telegram-bot
✅ 服务重启成功！

📦 处理服务: discord-bot
✅ 服务安装并启动成功！

📦 处理服务: webhook-server
✅ 服务重启成功！

📊 部署汇总:
   总服务数: 3
   成功: 3
   失败: 0
```

### 注意事项

- ⚠️ Hook 需要 `sudo` 权限来操作 systemd 服务，合并时可能需要输入密码
- ⚠️ 仅在 `master` 分支上执行合并操作时触发
- ⚠️ 服务名由 `.service` 文件名决定（例如 `telegram-bot.service` 的服务名为 `telegram-bot`）
- ✅ 支持同时部署多个服务，只需在 `deploy/` 目录下放置多个 `.service` 文件
- ✅ 如果某个服务启动失败，不会影响其他服务的部署

### 手动卸载 Hook

如果不想使用自动部署，可以删除 hook：

```bash
rm .git/hooks/post-merge
```

---

## 服务创建记录

### 2025-11-10 - Git Hook 自动部署

- ✅ 添加 `deploy/post-merge` Git Hook 脚本
- ✅ 添加 `deploy/install-hooks.sh` 安装脚本
- ✅ 实现 dev→master 合并时自动检测、安装/重启服务
- ✅ 添加详细的部署状态输出和错误处理

### 2025-11-10 - systemd 模板添加

- ✅ 在仓库 `deploy/telegram-bot.service` 中添加 systemd 单元模板
- ✅ 更新 `telebot/dreaife_test_bot.py`，默认使用 `/logs/bot/<bot_name>` 和 `/data/bot/<bot_name>`，支持通过 CLI 覆盖
- ✅ 在本文件记录安装与启动步骤

---

*最后更新: 2025-11-10*
