"""Pytest 配置：让 tests 目录能找到 scripts 包。"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
