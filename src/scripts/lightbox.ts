import type { Photo } from "../lib/photos";
import { formatDate, formatExif, formatPlatform } from "../lib/format";

const SWIPE_THRESHOLD = 60;

export default function init(photos: Photo[]): void {
  console.log("[lightbox] init called, photos:", photos.length);
  const dialog = document.getElementById("lightbox") as HTMLDialogElement | null;
  if (!dialog) { console.error("[lightbox] dialog#lightbox not found!"); return; }
  console.log("[lightbox] dialog found, binding handlers...");

  const img = document.getElementById("lb-img") as HTMLImageElement;
  const title = document.getElementById("lb-title")!;
  const author = document.getElementById("lb-author") as HTMLAnchorElement;
  const date = document.getElementById("lb-date")!;
  const platform = document.getElementById("lb-platform")!;
  const exifEl = document.getElementById("lb-exif")!;
  const original = document.getElementById("lb-original") as HTMLAnchorElement;
  const closeBtn = document.getElementById("lb-close")!;

  const byId = new Map<string, number>();
  photos.forEach((p, i) => byId.set(p.id, i));

  let current = -1;

  const base = (typeof document !== "undefined" && (document as any).baseURI) || "/";

  function render(index: number): void {
    const p = photos[index];
    if (!p) return;
    current = index;
    img.src = `${new URL(p.thumb_path, base).pathname}`;
    img.alt = p.title ?? p.author_name;
    title.textContent = p.title ?? "";
    author.textContent = p.author_name;
    author.href = p.author_url;
    date.textContent = formatDate(p.posted_at);
    platform.textContent = formatPlatform(p);
    exifEl.innerHTML = "";
    for (const line of formatExif(p.exif)) {
      const li = document.createElement("li");
      li.textContent = line;
      exifEl.appendChild(li);
    }
    original.href = p.original_url;
    location.hash = `#photo=${p.id}`;
  }

  function open(id: string): void {
    const i = byId.get(id);
    if (i === undefined) return;
    render(i);
    if (!dialog.hasAttribute("open")) dialog.showModal();
  }

  function close(): void {
    if (dialog.hasAttribute("open")) dialog.close();
    if (location.hash.startsWith("#photo=")) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    current = -1;
  }

  function step(delta: number): void {
    if (current < 0) return;
    const next = (current + delta + photos.length) % photos.length;
    render(next);
  }

  // Card clicks — 事件委托，不依赖 init 时 DOM 中是否有卡片
  document.addEventListener("click", (e) => {
    const card = (e.target as HTMLElement).closest(".card-trigger[data-id]");
    if (!card) return;
    const id = card.getAttribute("data-id");
    console.log("[lightbox] card clicked via delegation, data-id:", id);
    if (id) open(id);
  });

  // Keyboard
  document.addEventListener("keydown", (e) => {
    if (!dialog.hasAttribute("open")) return;
    if (e.key === "Escape") close();
    else if (e.key === "ArrowRight") step(1);
    else if (e.key === "ArrowLeft") step(-1);
  });

  // Close button + backdrop
  closeBtn.addEventListener("click", close);
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) close();
  });
  dialog.addEventListener("close", () => {
    if (location.hash.startsWith("#photo=")) {
      history.replaceState(null, "", location.pathname + location.search);
    }
    current = -1;
  });

  // Touch swipe
  let touchStart: { x: number; y: number } | null = null;
  dialog.addEventListener("touchstart", (e) => {
    const t = e.changedTouches[0];
    touchStart = { x: t.clientX, y: t.clientY };
  });
  dialog.addEventListener("touchend", (e) => {
    if (!touchStart) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchStart.x;
    const dy = t.clientY - touchStart.y;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_THRESHOLD) {
      step(dx < 0 ? 1 : -1);
    } else if (dy > SWIPE_THRESHOLD) {
      close();
    }
    touchStart = null;
  });

  // Initial hash
  const m = /^#photo=(.+)$/.exec(location.hash);
  if (m) open(decodeURIComponent(m[1]));
}
