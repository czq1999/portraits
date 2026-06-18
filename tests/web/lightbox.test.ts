import { describe, expect, it, beforeEach } from "vitest";
import init from "../../src/scripts/lightbox";
import type { Photo } from "../../src/lib/photos";

const PHOTOS: Photo[] = [
  {
    id: "a:1",
    source: "unsplash",
    source_kind: "topic:people",
    original_url: "https://example.com/a1",
    thumb_path: "thumbs/a-1.webp",
    author_name: "Jane",
    author_url: "https://example.com/jane",
    posted_at: "2026-06-17T09:00:00Z",
    exif: { camera: "Leica Q2" },
    title: "First",
  },
  {
    id: "a:2",
    source: "flickr",
    source_kind: "group:portraitart",
    original_url: "https://example.com/a2",
    thumb_path: "thumbs/a-2.webp",
    author_name: "John",
    author_url: "https://example.com/john",
    posted_at: "2026-06-16T09:00:00Z",
    exif: {},
  },
];

function setupDom() {
  document.body.innerHTML = `
    <button class="card-trigger" data-id="a:1"><img src="/thumbs/a-1.webp" /></button>
    <button class="card-trigger" data-id="a:2"><img src="/thumbs/a-2.webp" /></button>
    <dialog id="lightbox">
      <div class="lb-image"><img id="lb-img" /></div>
      <aside class="lb-info">
        <div id="lb-title"></div>
        <a id="lb-author" href="#"></a>
        <div id="lb-date"></div>
        <div id="lb-platform"></div>
        <ul id="lb-exif"></ul>
        <a id="lb-original" href="#">original →</a>
      </aside>
      <button id="lb-close">×</button>
    </dialog>
  `;
  // Polyfill HTMLDialogElement.showModal/close for happy-dom
  const dialog = document.getElementById("lightbox") as any;
  if (typeof dialog.showModal !== "function") {
    dialog.showModal = function () { this.setAttribute("open", ""); };
    dialog.close = function () { this.removeAttribute("open"); };
  }
}

describe("lightbox", () => {
  beforeEach(() => {
    location.hash = "";
    setupDom();
  });

  it("opens with the clicked photo's data", () => {
    init(PHOTOS);
    const card = document.querySelector('[data-id="a:1"]') as HTMLElement;
    card.click();
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    expect((document.getElementById("lb-title") as HTMLElement).textContent).toBe("First");
    expect((document.getElementById("lb-author") as HTMLAnchorElement).href).toContain("example.com/jane");
    expect((document.getElementById("lb-original") as HTMLAnchorElement).href).toContain("example.com/a1");
    expect(location.hash).toBe("#photo=a:1");
  });

  it("arrow right advances to next photo", () => {
    init(PHOTOS);
    (document.querySelector('[data-id="a:1"]') as HTMLElement).click();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
    expect((document.getElementById("lb-title") as HTMLElement).textContent).toBe("");
    expect(location.hash).toBe("#photo=a:2");
  });

  it("escape closes and clears hash", () => {
    init(PHOTOS);
    (document.querySelector('[data-id="a:1"]') as HTMLElement).click();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(false);
    expect(location.hash).toBe("");
  });

  it("opens from initial hash on init", () => {
    location.hash = "#photo=a:2";
    init(PHOTOS);
    const dialog = document.getElementById("lightbox") as HTMLDialogElement;
    expect(dialog.hasAttribute("open")).toBe(true);
    expect((document.getElementById("lb-platform") as HTMLElement).textContent).toBe(
      "FLICKR · GROUP: PORTRAITART"
    );
  });
});
