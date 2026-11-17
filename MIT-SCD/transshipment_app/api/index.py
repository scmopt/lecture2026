"""Vercel 用のエントリポイント

/api/* へのリクエストは vercel.json の rewrites でこの関数に転送され、
backend/main.py の FastAPI アプリがそのまま処理する。
"""

import os
import sys
from pathlib import Path

# Vercel の関数で書き込めるのは /tmp だけなので、AMPL の一時ファイルをそこに置く
os.environ.setdefault("TMPDIR", "/tmp")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app  # noqa: E402,F401
