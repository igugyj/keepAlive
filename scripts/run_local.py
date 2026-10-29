"""本地入口：把 src 加入路径后调用 main。"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

# Windows 控制台默认 GBK，日志里的 · 等字符会显示为乱码
sys.stdout.reconfigure(errors="replace")

from main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
