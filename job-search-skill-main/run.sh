#!/bin/bash

# 获取脚本所在目录，确保在任何地方调用都能找到文件
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查环境是否已安装
if [ ! -d ".venv" ]; then
    echo "错误: 环境未初始化。"
    echo "请先运行: ./setup.sh"
    exit 1
fi

# 激活虚拟环境并运行爬虫，传递所有参数 ($@)
source .venv/bin/activate
python crawl_jobs.py "$@"