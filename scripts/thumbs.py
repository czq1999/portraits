"""缩略图下载、转 WebP、批量删除。"""
import io
import logging
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


def download_and_convert(
    thumb_url: str,
    dest: Path,
    *,
    max_edge: int = 1200,
    quality: int = 80,
    client: httpx.Client | None = None,
) -> bool:
    """下载图片，按最长边缩放（不放大），转 WebP 写到 dest。

    任何错误（网络、解码）都返回 False，调用方跳过该照片即可。
    """
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0)
    try:
        try:
            resp = client.get(thumb_url, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("thumbnail download failed: %s (%s)", thumb_url, e)
            return False

        try:
            img = Image.open(io.BytesIO(resp.content))
            img.load()  # 强制解码以触发错误
        except (UnidentifiedImageError, OSError) as e:
            logger.warning("thumbnail decode failed: %s (%s)", thumb_url, e)
            return False

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        long_edge = max(img.size)
        if long_edge > max_edge:
            ratio = max_edge / long_edge
            new_size = (round(img.size[0] * ratio), round(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest, format="WEBP", quality=quality, method=4)
        return True
    finally:
        if owns_client:
            client.close()


def delete_thumbs(thumb_paths: list[str], base_dir: Path) -> None:
    """从 base_dir/<thumb_path> 删除一组缩略图，不存在的文件静默忽略。"""
    for rel in thumb_paths:
        target = base_dir / rel
        try:
            target.unlink()
        except OSError:
            pass
