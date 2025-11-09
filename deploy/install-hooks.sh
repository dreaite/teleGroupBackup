#!/bin/bash
# 安装 Git hooks 脚本
# 用法: ./deploy/install-hooks.sh

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo "❌ 错误: 当前不在 Git 仓库中"
    exit 1
fi

HOOKS_DIR="$REPO_ROOT/.git/hooks"
DEPLOY_DIR="$REPO_ROOT/deploy"

echo "========================================="
echo "🔧 安装 Git Hooks"
echo "========================================="

# 检查 deploy 目录
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "❌ 错误: deploy 目录不存在"
    exit 1
fi

# 安装 post-merge hook
if [ -f "$DEPLOY_DIR/post-merge" ]; then
    echo "📝 安装 post-merge hook..."
    cp "$DEPLOY_DIR/post-merge" "$HOOKS_DIR/post-merge"
    chmod +x "$HOOKS_DIR/post-merge"
    echo "✅ post-merge hook 安装成功"
else
    echo "⚠️  警告: $DEPLOY_DIR/post-merge 不存在，跳过"
fi

echo ""
echo "========================================="
echo "✅ Git Hooks 安装完成！"
echo "========================================="
echo ""
echo "📖 说明:"
echo "   当你将 dev 分支合并到 master 时，会自动:"
echo "   1. 检查 systemd 服务是否存在"
echo "   2. 如果存在：停止 → 更新 → 重启服务"
echo "   3. 如果不存在：安装 → 启用 → 启动服务"
echo ""
echo "⚙️  配置:"
echo "   服务名: dreaife_test_bot"
echo "   服务文件: deploy/telegram-bot.service"
echo ""
echo "🔒 权限要求:"
echo "   Hook 需要 sudo 权限来操作 systemd 服务"
echo "   合并时可能需要输入密码"
echo ""
echo "🧪 测试 hook:"
echo "   cd $REPO_ROOT"
echo "   git checkout dev"
echo "   # 做一些改动并提交"
echo "   git checkout master"
echo "   git merge dev"
echo ""
