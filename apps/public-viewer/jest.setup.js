import "@testing-library/jest-dom";

// jsdom には structuredClone が無く、Chakra の Provider（テーマ設定の複製）で落ちる。
// Node の v8 シリアライズで同等の複製を用意する。
if (typeof globalThis.structuredClone !== "function") {
  const v8 = require("node:v8");
  globalThis.structuredClone = (value) => v8.deserialize(v8.serialize(value));
}
