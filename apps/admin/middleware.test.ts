/**
 * @jest-environment node
 */
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

const basic = (credentials: string) => `Basic ${Buffer.from(credentials).toString("base64")}`;

const request = (authorization?: string) =>
  new NextRequest("http://localhost:4000/", {
    headers: authorization === undefined ? {} : { authorization },
  });

describe("admin middleware の Basic 認証", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv, BASIC_AUTH_USERNAME: "admin", BASIC_AUTH_PASSWORD: "p@ss:word" };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("':' を含むパスワードでも、正しい資格情報なら通す", () => {
    const res = middleware(request(basic("admin:p@ss:word")));
    expect(res.status).toBe(200);
    expect(res.headers.get("x-middleware-next")).toBe("1");
  });

  it("パスワードの前半だけ一致する資格情報は 401 にする", () => {
    expect(middleware(request(basic("admin:p@ss"))).status).toBe(401);
  });

  it("誤ったパスワードは 401 にする", () => {
    expect(middleware(request(basic("admin:wrong"))).status).toBe(401);
  });

  it.each([["Basic"], ["Basic "], ["Bearer token"], ["garbage"], [basic("no-colon")]])(
    "不正な Authorization ヘッダー %p は 500 ではなく 401 にする",
    (authorization) => {
      expect(middleware(request(authorization)).status).toBe(401);
    },
  );

  it("Authorization ヘッダーがなければ 401 にする", () => {
    expect(middleware(request()).status).toBe(401);
  });

  it("BASIC_AUTH が未設定なら素通しする", () => {
    process.env.BASIC_AUTH_USERNAME = "";
    expect(middleware(request()).headers.get("x-middleware-next")).toBe("1");
  });
});
