import { normalizeLanguage, persistLanguage, resolveInitialLanguage, withLanguageQuery } from "../languages";

function storage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
    data,
  };
}

describe("normalizeLanguage", () => {
  it.each([
    ["ja", "ja"],
    ["EN", "en"],
    ["ko-KR", "ko"],
    ["en_US", "en"],
    ["fr", undefined],
    ["", undefined],
    [undefined, undefined],
    [42, undefined],
  ])("%p -> %p", (input, expected) => {
    expect(normalizeLanguage(input)).toBe(expected);
  });
});

describe("resolveInitialLanguage", () => {
  it("URL のクエリを最優先する", () => {
    expect(resolveInitialLanguage("?lang=ko", storage({ "kouchou-ai.language": "en" }))).toBe("ko");
  });

  it("クエリが無ければ保存済みの選択を使う", () => {
    expect(resolveInitialLanguage("?foo=1", storage({ "kouchou-ai.language": "en" }))).toBe("en");
  });

  it("対応外の値は無視して既定（日本語）に戻す", () => {
    expect(resolveInitialLanguage("?lang=fr", storage({ "kouchou-ai.language": "zz" }))).toBe("ja");
    expect(resolveInitialLanguage("", null)).toBe("ja");
  });

  it("localStorage が例外を投げても既定に戻す", () => {
    const broken = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(resolveInitialLanguage("", broken)).toBe("ja");
    expect(() => persistLanguage("en", broken)).not.toThrow();
  });
});

describe("withLanguageQuery", () => {
  it("他のクエリを保ったまま lang を付け替える", () => {
    expect(withLanguageQuery("?a=1&lang=en", "ko")).toBe("?a=1&lang=ko");
    expect(withLanguageQuery("", "en")).toBe("?lang=en");
  });

  it("既定言語では lang を外す", () => {
    expect(withLanguageQuery("?lang=en&a=1", "ja")).toBe("?a=1");
    expect(withLanguageQuery("?lang=en", "ja")).toBe("");
  });
});
