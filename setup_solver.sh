#!/usr/bin/env bash
# ────────────────────────────────────────────────
# M2API Turnstile 过盾引擎 一键部署
# 启动后监听 127.0.0.1:5072
# ────────────────────────────────────────────────
set -e

SOLVER_DIR="$HOME/m2api-turnstile-solver"
REPO="https://github.com/M2API/turnstile-solver.git"

# 0. 预检
command -v python3 >/dev/null 2>&1 || { echo "❌ 需要 python3，请先安装。"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "❌ 需要 git，请先安装。"; exit 1; }

# 1. 克隆 / 更新
if [ -d "$SOLVER_DIR" ]; then
    echo "📦 目录已存在，git pull ..."
    cd "$SOLVER_DIR" && git pull
else
    echo "📦 克隆 M2API turnstile-solver ..."
    git clone "$REPO" "$SOLVER_DIR"
    cd "$SOLVER_DIR"
fi

# 2. 创建虚拟环境 + 装依赖
if [ ! -d ".venv" ]; then
    echo "🐍 创建虚拟环境 ..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "📦 安装依赖 ..."
pip install -r requirements.txt -q

# 3. 安装 Playwright Firefox (Camoufox 依赖)
echo "🌐 安装 Playwright Firefox ..."
python3 -m playwright install firefox

# 4. 启动引擎
echo ""
echo "🔑 M2API Turnstile 过盾引擎启动在 127.0.0.1:5072"
echo "   保持此终端运行，另开终端执行: python3 register_m2api.py"
echo ""
python3 api_solver.py --port 5072 --browser_type camoufox
