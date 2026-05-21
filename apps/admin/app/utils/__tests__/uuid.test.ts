import { createUUID } from "../uuid";

describe("createUUID", () => {
  const originalCrypto = global.crypto;
  const originalMathRandom = Math.random;

  afterEach(() => {
    Object.defineProperty(global, "crypto", {
      configurable: true,
      value: originalCrypto,
    });
    Math.random = originalMathRandom;
  });

  it("uses crypto.randomUUID when available", () => {
    const randomUUID = jest.fn(() => "native-uuid");
    Object.defineProperty(global, "crypto", {
      configurable: true,
      value: { randomUUID },
    });

    expect(createUUID()).toBe("native-uuid");
    expect(randomUUID).toHaveBeenCalledTimes(1);
  });

  it("falls back to crypto.getRandomValues when randomUUID is unavailable", () => {
    const getRandomValues = jest.fn((bytes: Uint8Array) => {
      bytes.set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
      return bytes;
    });
    Object.defineProperty(global, "crypto", {
      configurable: true,
      value: { getRandomValues },
    });

    expect(createUUID()).toBe("00010203-0405-4607-8809-0a0b0c0d0e0f");
    expect(getRandomValues).toHaveBeenCalledTimes(1);
  });

  it("falls back to Math.random when crypto is unavailable", () => {
    const values = Array.from({ length: 16 }, (_, index) => index / 255);
    let current = 0;
    Math.random = jest.fn(() => values[current++] ?? 0);
    Object.defineProperty(global, "crypto", {
      configurable: true,
      value: undefined,
    });

    expect(createUUID()).toBe("00010203-0405-4607-8809-0a0b0c0d0e0f");
  });
});
