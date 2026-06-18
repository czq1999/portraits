"""适配器注册表。每个具体适配器模块在自身被 import 时把自己注册进 ADAPTERS。"""
from collections.abc import Callable

import httpx

from scripts.models import NormalizedPhoto

FetchFn = Callable[[dict, httpx.Client], list[NormalizedPhoto]]
ADAPTERS: dict[str, FetchFn] = {}


def register(platform: str, fn: FetchFn) -> None:
    ADAPTERS[platform] = fn


# 自动 import 各适配器模块以触发 register() 调用
from scripts.adapters import unsplash  # noqa: E402,F401
