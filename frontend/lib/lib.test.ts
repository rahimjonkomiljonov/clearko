import { describe, expect, it } from "vitest";
import { checkFile, checkSelection, MAX_FILE_BYTES } from "./files";
import { errorText, guessLang, TEXTS } from "./i18n";
import { parseStage } from "./progress";
import { sortFlags } from "./flags";

const jpg = { name: "a.jpg", type: "image/jpeg", size: 1000 };

describe("parseStage", () => {
  it("maps the backend stage strings to steps", () => {
    expect(parseStage("queued", "queued").step).toBe("queued");
    expect(parseStage("running", "starting").step).toBe("reading");
    expect(parseStage("running", "page 2/8 read")).toMatchObject({ step: "reading", detail: "2/8" });
    expect(parseStage("running", "summarizing").step).toBe("summarizing");
    expect(parseStage("running", "reviewing clauses 3/6")).toMatchObject({ step: "reviewing", detail: "3/6" });
    expect(parseStage("running", "translating to uz").step).toBe("translating");
    expect(parseStage("running", "translating 2/5")).toMatchObject({ step: "translating", detail: "2/5" });
    expect(parseStage("done", "done")).toMatchObject({ step: "done", percent: 100 });
  });

  it("never goes backwards through the steps", () => {
    const order = ["page 8/8 read", "summarizing", "reviewing clauses 1/6", "reviewing clauses 6/6", "translating 1/5"];
    const pct = order.map((s) => parseStage("running", s).percent);
    expect(pct).toEqual([...pct].sort((a, b) => a - b));
    expect(Math.max(...pct)).toBeLessThan(100);
  });

  it("copes with an unknown stage", () => {
    expect(parseStage("running", "something new").step).toBe("queued");
  });
});

describe("file checks", () => {
  it("accepts images and PDFs", () => {
    expect(checkFile(jpg)).toBeNull();
    expect(checkFile({ name: "c.pdf", type: "application/pdf", size: 5 })).toBeNull();
    expect(checkFile({ name: "x.JPG", type: "", size: 5 })).toBeNull(); // some phones send no type
  });

  it("gives HEIC its own code and rejects other files", () => {
    expect(checkFile({ name: "IMG.HEIC", type: "image/heic", size: 5 })).toBe("heic");
    expect(checkFile({ name: "IMG.heic", type: "", size: 5 })).toBe("heic");
    expect(checkFile({ name: "a.txt", type: "text/plain", size: 5 })).toBe("bad_file");
  });

  it("limits size and count", () => {
    expect(checkFile({ ...jpg, size: MAX_FILE_BYTES + 1 })).toBe("too_large");
    expect(checkSelection([])).toBe("no_files");
    expect(checkSelection(Array(11).fill(jpg))).toBe("too_many");
    expect(checkSelection(Array(4).fill({ ...jpg, size: MAX_FILE_BYTES }))).toBe("too_large"); // 48 MB total
  });
});

describe("language", () => {
  it("guesses from the browser languages", () => {
    expect(guessLang(["uz-UZ", "en"])).toBe("uz");
    expect(guessLang(["ko-KR", "ru-RU"])).toBe("ru");
    expect(guessLang(["ko-KR"])).toBe("en");
    expect(guessLang([])).toBe("en");
  });

  it("prefers the API message, falls back to ours", () => {
    expect(errorText(TEXTS.ru, "blurry", "от сервера")).toBe("от сервера");
    expect(errorText(TEXTS.uz, "network", "")).toBe(TEXTS.uz.errors.network);
    expect(errorText(TEXTS.en, "never_heard_of_it", "")).toBe(TEXTS.en.errors.internal);
  });

  it("has every error code in every language", () => {
    const codes = Object.keys(TEXTS.en.errors).sort();
    expect(Object.keys(TEXTS.ru.errors).sort()).toEqual(codes);
    expect(Object.keys(TEXTS.uz.errors).sort()).toEqual(codes);
  });
});

describe("red flag order", () => {
  it("puts serious flags first and keeps document order inside a level", () => {
    const f = (title: string, severity: "low" | "medium" | "high") =>
      ({ title, severity }) as Parameters<typeof sortFlags>[0][number];
    const out = sortFlags([f("a", "low"), f("b", "high"), f("c", "medium"), f("d", "high")]);
    expect(out.map((x) => x.title)).toEqual(["b", "d", "c", "a"]);
  });
});
