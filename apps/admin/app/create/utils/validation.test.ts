import { isValidId, validateReportId } from "./validation";

describe("isValidId", () => {
  test("有効なIDの場合はtrueを返す", () => {
    expect(isValidId("example")).toBe(true);
    expect(isValidId("my-report")).toBe(true);
    expect(isValidId("test123")).toBe(true);
    expect(isValidId("report-v2")).toBe(true);
    expect(isValidId("a")).toBe(true);
    expect(isValidId("123")).toBe(true);
  });

  test("無効なIDの場合はfalseを返す", () => {
    expect(isValidId("")).toBe(false);
    expect(isValidId("-example")).toBe(false);
    expect(isValidId("example-")).toBe(false);
    expect(isValidId("Example")).toBe(false);
    expect(isValidId("test_report")).toBe(false);
    expect(isValidId("test report")).toBe(false);
    expect(isValidId("test@example")).toBe(false);
  });

  test("255文字以下の場合はtrueを返す", () => {
    const validId = "a".repeat(255);
    expect(isValidId(validId)).toBe(true);
  });

  test("255文字を超える場合はfalseを返す", () => {
    const invalidId = "a".repeat(256);
    expect(isValidId(invalidId)).toBe(false);
  });
});

describe("validateReportId", () => {
  describe("有効なIDの場合", () => {
    test("有効なIDはisValid: trueを返す", () => {
      const testCases = [
        "example",
        "my-report",
        "test123",
        "report-v2",
        "user-feedback-analysis",
        "a",
        "123",
        "abc-def-ghi",
      ];

      for (const id of testCases) {
        const result = validateReportId(id);
        expect(result).toEqual({ isValid: true });
      }
    });

    test("255文字の場合はisValid: trueを返す", () => {
      const validId = "a".repeat(255);
      const result = validateReportId(validId);
      expect(result).toEqual({ isValid: true });
    });

    test("数字のみのIDは有効", () => {
      expect(validateReportId("123")).toEqual({ isValid: true });
      expect(validateReportId("456789")).toEqual({ isValid: true });
    });

    test("英字のみのIDは有効", () => {
      expect(validateReportId("abc")).toEqual({ isValid: true });
      expect(validateReportId("example")).toEqual({ isValid: true });
    });

    test("英字と数字の組み合わせは有効", () => {
      expect(validateReportId("test123")).toEqual({ isValid: true });
      expect(validateReportId("123test")).toEqual({ isValid: true });
      expect(validateReportId("a1b2c3")).toEqual({ isValid: true });
    });

    test("適切に配置されたハイフンは有効", () => {
      expect(validateReportId("a-b")).toEqual({ isValid: true });
      expect(validateReportId("test-report-123")).toEqual({ isValid: true });
      expect(validateReportId("very-long-report-name-with-many-hyphens")).toEqual({ isValid: true });
    });
  });

  describe("無効なIDの場合", () => {
    test("空文字の場合は適切なエラーメッセージを返す", () => {
      const result = validateReportId("");
      expect(result).toEqual({
        isValid: false,
        errorMessage: "IDを入力してください",
      });
    });

    test("255文字を超える場合は適切なエラーメッセージを返す", () => {
      const invalidId = "a".repeat(256);
      const result = validateReportId(invalidId);
      expect(result).toEqual({
        isValid: false,
        errorMessage: "IDは255文字以内で入力してください",
      });
    });

    test("使用禁止文字が含まれる場合は適切なエラーメッセージを返す", () => {
      const testCases = [
        "Example",
        "test_report",
        "test report",
        "test@example",
        "テスト",
        "test.example",
        "test/example",
      ];

      for (const id of testCases) {
        const result = validateReportId(id);
        expect(result).toEqual({
          isValid: false,
          errorMessage: "IDは英小文字、数字、ハイフンのみ使用できます",
        });
      }
    });

    test("ハイフンで始まる場合は適切なエラーメッセージを返す", () => {
      const result = validateReportId("-example");
      expect(result).toEqual({
        isValid: false,
        errorMessage: "IDはハイフンで始めることができません",
      });
    });

    test("ハイフンで終わる場合は適切なエラーメッセージを返す", () => {
      const result = validateReportId("example-");
      expect(result).toEqual({
        isValid: false,
        errorMessage: "IDはハイフンで終わることができません",
      });
    });
  });
});
