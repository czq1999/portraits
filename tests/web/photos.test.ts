import { describe, expect, it } from "vitest";
import { loadPhotos } from "../../src/lib/photos";
import { promises as fs } from "node:fs";
import path from "node:path";

describe("loadPhotos", () => {
  it("returns empty when data file missing", async () => {
    const tmp = await fs.mkdtemp("/tmp/ph-");
    const photos = await loadPhotos(path.join(tmp, "missing.json"));
    expect(photos).toEqual([]);
  });

  it("sorts by posted_at desc", async () => {
    const tmp = await fs.mkdtemp("/tmp/ph-");
    const file = path.join(tmp, "p.json");
    await fs.writeFile(
      file,
      JSON.stringify([
        { id: "a:1", posted_at: "2026-01-01T00:00:00Z" },
        { id: "a:2", posted_at: "2026-03-01T00:00:00Z" },
        { id: "a:3", posted_at: "2026-02-01T00:00:00Z" },
      ])
    );
    const photos = await loadPhotos(file);
    expect(photos.map((p) => p.id)).toEqual(["a:2", "a:3", "a:1"]);
  });
});
