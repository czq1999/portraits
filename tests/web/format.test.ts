import { describe, expect, it } from "vitest";
import { formatDate, formatExif, formatPlatform } from "../../src/lib/format";

describe("formatDate", () => {
  it("formats ISO into uppercase short month + day + year", () => {
    expect(formatDate("2026-06-17T09:12:00Z")).toBe("JUN 17, 2026");
  });
});

describe("formatPlatform", () => {
  it("formats source + source_kind", () => {
    expect(
      formatPlatform({ source: "flickr", source_kind: "group:portraitart" } as any)
    ).toBe("FLICKR · GROUP: PORTRAITART");
  });
});

describe("formatExif", () => {
  it("returns only present fields", () => {
    expect(
      formatExif({ camera: "Leica Q2", aperture: "f/1.7", iso: 400 } as any)
    ).toEqual(["Leica Q2", "f/1.7", "ISO 400"]);
  });

  it("returns empty for empty exif", () => {
    expect(formatExif({})).toEqual([]);
  });
});
