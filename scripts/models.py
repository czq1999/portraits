"""统一的图片数据模型，所有适配器输出都要变成它。"""
from dataclasses import dataclass, field


def make_id(platform: str, photo_id: str) -> str:
    """全局唯一 ID 格式：<platform>:<photo_id>。"""
    return f"{platform}:{photo_id}"


def thumb_path_for(photo_id: str) -> str:
    """从 'flickr:12345' 推导出 'thumbs/flickr-12345.webp'。"""
    platform, raw_id = photo_id.split(":", 1)
    return f"thumbs/{platform}-{raw_id}.webp"


@dataclass
class NormalizedPhoto:
    """所有平台 API 响应被适配器转换成这个统一形态。"""

    id: str
    source: str
    source_kind: str
    original_url: str
    thumb_url: str  # 抓取阶段使用，不持久化
    author_name: str
    author_url: str
    title: str | None
    taken_at: str | None
    posted_at: str
    exif: dict[str, str | int | None] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """输出 photos.json 中一条记录的形态。"""
        d: dict = {
            "id": self.id,
            "source": self.source,
            "source_kind": self.source_kind,
            "original_url": self.original_url,
            "thumb_path": thumb_path_for(self.id),
            "author_name": self.author_name,
            "author_url": self.author_url,
            "posted_at": self.posted_at,
            "exif": self.exif,
        }
        if self.title is not None:
            d["title"] = self.title
        if self.taken_at is not None:
            d["taken_at"] = self.taken_at
        return d
