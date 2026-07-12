/**
 * Phase 2 unit tests for video URL parsing.
 * Run: cd /app/frontend && yarn test src/lib/video.test.js --watchAll=false
 */
import { detectVideoProvider, toDriveEmbedUrl, driveFileId } from "./video";

describe("detectVideoProvider", () => {
  test("empty", () => expect(detectVideoProvider("")).toBe("empty"));
  test("YouTube long", () => expect(detectVideoProvider("https://www.youtube.com/watch?v=abc")).toBe("youtube"));
  test("YouTube short", () => expect(detectVideoProvider("https://youtu.be/abc")).toBe("youtube"));
  test("Drive share", () => expect(detectVideoProvider("https://drive.google.com/file/d/1abc/view?usp=sharing")).toBe("drive"));
  test("Drive docs", () => expect(detectVideoProvider("https://docs.google.com/uc?id=1abc")).toBe("drive"));
  test("mp4", () => expect(detectVideoProvider("https://example.com/video.mp4")).toBe("external"));
});

describe("toDriveEmbedUrl", () => {
  test("share link", () => {
    expect(toDriveEmbedUrl("https://drive.google.com/file/d/1ABC-xyz_123/view?usp=sharing"))
      .toBe("https://drive.google.com/file/d/1ABC-xyz_123/preview");
  });
  test("already-preview URL", () => {
    expect(toDriveEmbedUrl("https://drive.google.com/file/d/1abc/preview"))
      .toBe("https://drive.google.com/file/d/1abc/preview");
  });
  test("open?id= URL", () => {
    expect(toDriveEmbedUrl("https://drive.google.com/open?id=1abc-xyz"))
      .toBe("https://drive.google.com/file/d/1abc-xyz/preview");
  });
  test("uc?id= URL", () => {
    expect(toDriveEmbedUrl("https://drive.google.com/uc?id=1abc&export=view"))
      .toBe("https://drive.google.com/file/d/1abc/preview");
  });
  test("docs.google uc", () => {
    expect(toDriveEmbedUrl("https://docs.google.com/uc?id=1abcDEF-_"))
      .toBe("https://drive.google.com/file/d/1abcDEF-_/preview");
  });
  test("garbage URL returns null", () => {
    expect(toDriveEmbedUrl("https://example.com/nothing")).toBeNull();
    expect(toDriveEmbedUrl("")).toBeNull();
    expect(toDriveEmbedUrl(null)).toBeNull();
  });
});

describe("driveFileId", () => {
  test("share link", () => expect(driveFileId("https://drive.google.com/file/d/XYZ/view")).toBe("XYZ"));
  test("id param", () => expect(driveFileId("https://drive.google.com/uc?id=XYZ")).toBe("XYZ"));
  test("not drive", () => expect(driveFileId("https://youtu.be/abc")).toBeNull());
});
