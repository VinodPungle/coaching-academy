import { syllabusFileError, SYLLABUS_MAX_BYTES } from "./syllabus";

describe("syllabusFileError", () => {
  it("accepts a normal PDF", () => {
    expect(syllabusFileError({ name: "syllabus.pdf", size: 1024 })).toBeNull();
  });

  it("accepts uppercase extension", () => {
    expect(syllabusFileError({ name: "SYLLABUS.PDF", size: 1024 })).toBeNull();
  });

  it("accepts a PDF exactly at the size limit", () => {
    expect(syllabusFileError({ name: "big.pdf", size: SYLLABUS_MAX_BYTES })).toBeNull();
  });

  it("rejects a missing file", () => {
    expect(syllabusFileError(null)).toBe("No file selected");
    expect(syllabusFileError(undefined)).toBe("No file selected");
  });

  it("rejects non-PDF extensions", () => {
    expect(syllabusFileError({ name: "syllabus.docx", size: 1024 })).toBe("Syllabus must be a PDF file");
    expect(syllabusFileError({ name: "notes.txt", size: 1024 })).toBe("Syllabus must be a PDF file");
    expect(syllabusFileError({ name: "image.png", size: 1024 })).toBe("Syllabus must be a PDF file");
  });

  it("rejects files with no extension or sneaky names", () => {
    expect(syllabusFileError({ name: "syllabus", size: 1024 })).toBe("Syllabus must be a PDF file");
    expect(syllabusFileError({ name: "syllabus.pdf.exe", size: 1024 })).toBe("Syllabus must be a PDF file");
    expect(syllabusFileError({ name: "", size: 1024 })).toBe("Syllabus must be a PDF file");
  });

  it("rejects oversized PDFs", () => {
    expect(syllabusFileError({ name: "huge.pdf", size: SYLLABUS_MAX_BYTES + 1 })).toBe(
      "Syllabus PDF is too large (max 25 MB)"
    );
  });
});
