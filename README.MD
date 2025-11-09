# Bot 服务管理文档

> 📅 创建日期: 2025年11月9日  
> 🐍 Python 版本: 3.14.0  
> 📦 虚拟环境: venv

---

## 📋 目录

1. [环境配置](#环境配置)
2. [启动服务](#启动服务)
3. [升级服务](#升级服务)
4. [依赖管理](#依赖管理)
5. [日志管理](#日志管理)
6. [常见问题](#常见问题)

---

## 🔧 环境配置

### 初次设置（已完成）

虚拟环境已创建，位置: `/home/dreaife/bot/venv`

```bash
# 如果需要重新创建虚拟环境（慎用！会删除现有环境）
rm -rf venv
python3 -m venv venv
```

### 激活虚拟环境

**每次使用前必须执行:**

```bash
cd /home/dreaife/bot
source venv/bin/activate
```

激活后，终端提示符前会显示 `(venv)`

### 停用虚拟环境

```bash
deactivate
```

---

## 🚀 启动服务

### 方式一：前台运行（推荐用于调试）

```bash
# 1. 进入项目目录
cd /home/dreaife/bot

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 启动机器人
python telebot/dreaife_test_bot.py
```

### 方式二：后台运行（推荐用于生产环境）

```bash
# 1. 进入项目目录并激活环境
cd /home/dreaife/bot
source venv/bin/activate

# 2. 使用 nohup 后台运行
nohup python telebot/dreaife_test_bot.py > bot_output.log 2>&1 &

# 3. 记录进程ID
echo $! > bot.pid
```

### 查看后台服务状态

```bash
# 查看进程是否运行
ps aux | grep dreaife_test_bot

# 或使用保存的PID文件
cat bot.pid | xargs ps -p
```

### 停止后台服务

```bash
# 方式一：使用PID文件
cat bot.pid | xargs kill

# 方式二：查找并结束进程
pkill -f dreaife_test_bot.py
```

### 使用 systemd 管理服务（推荐）

创建服务文件 `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
Type=simple
User=dreaife
WorkingDirectory=/home/dreaife/bot
Environment="PATH=/home/dreaife/bot/venv/bin"
ExecStart=/home/dreaife/bot/venv/bin/python /home/dreaife/bot/telebot/dreaife_test_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

管理命令：

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start telegram-bot

# 停止服务
sudo systemctl stop telegram-bot

# 重启服务
sudo systemctl restart telegram-bot

# 查看状态
sudo systemctl status telegram-bot

# 开机自启
sudo systemctl enable telegram-bot

# 取消开机自启
sudo systemctl disable telegram-bot

# 查看日志
sudo journalctl -u telegram-bot -f
```

---

## 🔄 升级服务

### 更新代码后重启

```bash
# 1. 拉取最新代码（如果使用 Git）
cd /home/dreaife/bot
git pull

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 更新依赖（如果有变化）
pip install -r requirements.txt

# 4. 重启服务
# 如果是前台运行：按 Ctrl+C 停止，然后重新运行
# 如果是后台运行：
cat bot.pid | xargs kill
nohup python telebot/dreaife_test_bot.py > bot_output.log 2>&1 &
echo $! > bot.pid

# 如果使用 systemd：
sudo systemctl restart telegram-bot
```

### 升级 Python 版本

```bash
# 1. 安装新版本 Python（使用 pyenv）
pyenv install 3.x.x

# 2. 删除旧虚拟环境
cd /home/dreaife/bot
rm -rf venv

# 3. 使用新 Python 版本创建虚拟环境
~/.pyenv/versions/3.x.x/bin/python3 -m venv venv

# 4. 激活并安装依赖
source venv/bin/activate
pip install -r requirements.txt

# 5. 更新 pyvenv.cfg 记录（自动完成）
```

---

## 📦 依赖管理

### 当前已安装的依赖

```text
openai==1.72.0              # OpenAI API 客户端
python-telegram-bot==22.0   # Telegram Bot SDK
python-dotenv==1.1.0        # 环境变量管理
pydantic==2.11.3            # 数据验证
httpx==0.28.1               # HTTP 客户端
tqdm==4.67.1                # 进度条工具
```

完整依赖列表见 `requirements.txt`

### 安装新依赖

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装单个包
pip install <package-name>

# 3. 安装指定版本
pip install <package-name>==<version>

# 4. 更新 requirements.txt
pip freeze > requirements.txt

# 5. 提交更新（如果使用 Git）
git add requirements.txt
git commit -m "Add new dependency: <package-name>"
```

### 更新现有依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新单个包
pip install --upgrade <package-name>

# 更新所有包（慎用！）
pip list --outdated
pip install --upgrade <package-name1> <package-name2>

# 更新后保存
pip freeze > requirements.txt
```

### 卸载依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 卸载包
pip uninstall <package-name>

# 更新 requirements.txt
pip freeze > requirements.txt
```

### 从 requirements.txt 安装所有依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装所有依赖
pip install -r requirements.txt
```

---

## 📊 日志管理

### 日志位置

```bash
# Bot 运行日志
/logs/bot/telebot/dreaife_test_bot/bot.log

# 后台运行输出日志（如果使用 nohup）
/home/dreaife/bot/bot_output.log
```

### 查看实时日志

```bash
# 查看 Bot 日志
tail -f /logs/bot/telebot/dreaife_test_bot/bot.log

# 查看后台运行日志
tail -f /home/dreaife/bot/bot_output.log

# 查看 systemd 服务日志
sudo journalctl -u telegram-bot -f
```

### 日志轮转配置

当前配置：
- 每天午夜自动轮转
- 保留最近 30 天的日志
- 格式：`bot.log.YYYY-MM-DD`

### 清理旧日志

```bash
# 删除 30 天前的日志
find /logs/bot/telebot/dreaife_test_bot/ -name "bot.log.*" -mtime +30 -delete
```

---

## ❓ 常见问题

### 1. 虚拟环境激活失败

**问题**: `source: command not found`

**解决**: 确保使用 zsh/bash shell，而不是 sh

```bash
# 检查当前 shell
echo $SHELL

# 切换到 zsh
zsh
```

### 2. 依赖安装失败

**问题**: `pip install` 报错

**解决**:

```bash
# 更新 pip
pip install --upgrade pip

# 清除缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

### 3. 端口被占用

**问题**: Bot 无法启动

**解决**:

```bash
# 查找占用进程
ps aux | grep dreaife_test_bot

# 结束进程
kill <PID>
```

### 4. 环境变量未加载

**问题**: API Key 等配置无效

**解决**:

```bash
# 检查 .env 文件是否存在
ls -la /home/dreaife/bot/.env

# 确认 python-dotenv 已安装
pip list | grep python-dotenv

# 重启服务
```

### 5. 权限问题

**问题**: 日志目录无法创建

**解决**:

```bash
# 创建日志目录
sudo mkdir -p /logs/bot/telebot/dreaife_test_bot/

# 设置权限
sudo chown -R dreaife:dreaife /logs/bot/
```

---

## 🔒 安全提示

1. **不要提交敏感信息到 Git**
   ```bash
   # 确保 .env 在 .gitignore 中
   echo ".env" >> .gitignore
   ```

2. **定期更新依赖**
   ```bash
   # 检查安全漏洞
   pip install safety
   safety check
   ```

3. **使用环境变量存储密钥**
   - TOKEN 应该从 `.env` 文件读取
   - 不要硬编码在代码中

---

## 📝 快速命令参考

```bash
# 启动（前台）
cd /home/dreaife/bot && source venv/bin/activate && python telebot/dreaife_test_bot.py

# 启动（后台）
cd /home/dreaife/bot && source venv/bin/activate && nohup python telebot/dreaife_test_bot.py > bot_output.log 2>&1 & echo $! > bot.pid

# 停止
cat bot.pid | xargs kill

# 查看日志
tail -f /logs/bot/telebot/dreaife_test_bot/bot.log

# 安装依赖
source venv/bin/activate && pip install -r requirements.txt

# 更新依赖列表
source venv/bin/activate && pip freeze > requirements.txt
```

---

## 📞 联系信息

如有问题，请参考：
- Python 官方文档: https://docs.python.org/
- python-telegram-bot 文档: https://docs.python-telegram-bot.org/
- OpenAI API 文档: https://platform.openai.com/docs/

---

*最后更新: 2025年11月9日*
