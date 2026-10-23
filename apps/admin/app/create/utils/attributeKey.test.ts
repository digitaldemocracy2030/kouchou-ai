import { toAttributeKey } from "./attributeKey";

describe("toAttributeKey", () => {
  test("接頭辞の無い列名には attribute_ を付ける", () => {
    expect(toAttributeKey("地域")).toBe("attribute_地域");
    expect(toAttributeKey("age")).toBe("attribute_age");
  });

  test("既に attribute_ で始まる列名はそのまま返す", () => {
    expect(toAttributeKey("attribute_地域")).toBe("attribute_地域");
    expect(toAttributeKey("attribute_author")).toBe("attribute_author");
  });

  test("attribute_ を途中に含むだけの列名には付ける", () => {
    expect(toAttributeKey("my_attribute_x")).toBe("attribute_my_attribute_x");
    expect(toAttributeKey("attribute")).toBe("attribute_attribute");
  });
});
