"""本地入口：把 src 加入路径后调用 main。"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
