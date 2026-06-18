import type { Photo } from "./photos";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const m = MONTHS[d.getUTCMonth()];
  const day = d.getUTCDate();
  const y = d.getUTCFullYear();
  return `${m} ${day}, ${y}`;
}

export function formatPlatform(photo: Pick<Photo, "source" | "source_kind">): string {
  const kind = photo.source_kind.replace(":", ": ");
  return `${photo.source.toUpperCase()} · ${kind.toUpperCase()}`;
}

const EXIF_ORDER: { key: string; render: (v: string | number) => string }[] = [
  { key: "camera", render: (v) => String(v) },
  { key: "lens", render: (v) => String(v) },
  { key: "focal_length", render: (v) => String(v) },
  { key: "aperture", render: (v) => String(v) },
  { key: "shutter", render: (v) => String(v) },
  { key: "iso", render: (v) => `ISO ${v}` },
];

export function formatExif(exif: Photo["exif"]): string[] {
  const out: string[] = [];
  for (const { key, render } of EXIF_ORDER) {
    const v = exif?.[key];
    if (v !== undefined && v !== null && v !== "") {
      out.push(render(v as string | number));
    }
  }
  return out;
}
