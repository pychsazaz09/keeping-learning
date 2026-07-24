# interview-agent
写了一个简易的面试题库CLI，支持添加、搜索、随机抽题、数据持久化到json

# 快速开始
python -m venv venv
venv/Scripts/pip install -e .
python cli.py add "Python的GIL是什么？" -t "Python基础" -d medium
python cli.py list
python cli.py random -n 1

# 技术栈
Python 3.12 + Pydantic + aiofiles + argparse
