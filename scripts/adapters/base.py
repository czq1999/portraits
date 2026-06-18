"""适配器之间共享的 HTTP 客户端工厂和错误类型。"""
import httpx

USER_AGENT = "portrait-photo-site/1.0 (+https://github.com/)"


class AdapterError(Exception):
    """适配器抓取失败时抛出，调度器捕获后会跳过该源继续其他源。"""


def make_client(extra_headers: dict[str, str] | None = None) -> httpx.Client:
    """统一的 httpx.Client：30s 超时、固定 UA、调用方自行管理生命周期。"""
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    return httpx.Client(timeout=30.0, headers=headers, follow_redirects=True)
