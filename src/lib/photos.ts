import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface Photo {
  id: string;
  source: string;
  source_kind: string;
  original_url: string;
  thumb_path: string;
  author_name: string;
  author_url: string;
  title?: string;
  taken_at?: string;
  posted_at: string;
  exif: Record<string, string | number | null>;
}

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_DATA_PATH = path.resolve(__dirname, "..", "..", "data", "photos.json");

export async function loadPhotos(file: string = DEFAULT_DATA_PATH): Promise<Photo[]> {
  let raw: string;
  try {
    raw = await fs.readFile(file, "utf-8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw e;
  }
  if (!raw.trim()) return [];
  const photos = JSON.parse(raw) as Photo[];
  return photos.sort((a, b) => (a.posted_at < b.posted_at ? 1 : -1));
}
