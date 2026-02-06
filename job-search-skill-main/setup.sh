#!/bin/bash

# 获取脚本所在目录，确保在任何地方调用都能找到文件
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Job Crawler Skill 环境初始化 ===${NC}"
echo -e "工作目录: $(pwd)"

# 1. 检查 Python 环境
echo -e "${YELLOW}[1/4] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未检测到 python3。请先安装 Python 3.8 或以上版本。${NC}"
    exit 1
fi
python3 --version

# 2. 创建虚拟环境
echo -e "${YELLOW}[2/4] 配置虚拟环境 (.venv)...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "虚拟环境已创建。"
else
    echo "虚拟环境已存在，跳过创建。"
fi

# 3. 安装 Python 依赖
echo -e "${YELLOW}[3/4] 安装依赖包...${NC}"
source .venv/bin/activate
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "找到 requirements.txt，开始安装..."
    pip install -r requirements.txt
else
    echo -e "${RED}错误: 找不到 requirements.txt${NC}"
    echo "当前目录文件列表:"
    ls -la
    exit 1
fi

# 4. 安装 Playwright 浏览器
echo -e "${YELLOW}[4/4] 安装 Chromium 浏览器驱动...${NC}"
playwright install chromium

echo -e "${GREEN}=== ✅ 安装完成！ ===${NC}"
echo -e "现在你可以使用以下命令运行爬虫："
echo -e "  ${GREEN}./run.sh --keywords '你的关键词'${NC}"
