import { createReport } from "./createReport";

jest.mock("@/app/utils/api", () => ({
  getApiBaseUrl: () => "http://localhost:8000",
}));

const mockFetch = jest.fn();
global.fetch = mockFetch;

const baseParams: Parameters<typeof createReport>[0] = {
  input: "report-1",
  question: "",
  intro: "",
  comments: [],
  cluster: [3, 6],
  provider: "openai",
  model: "gpt-4o-mini",
  workers: 1,
  prompt: { extraction: "", initialLabelling: "", mergeLabelling: "", overview: "" },
  analysis_mode: "hierarchical",
  is_pubcom: false,
  inputType: "file",
  is_embedded_at_local: false,
  enable_source_link: false,
};

const errorResponse = (status: number, statusText: string, body: unknown) =>
  ({
    ok: false,
    status,
    statusText,
    json: jest.fn().mockResolvedValue(body),
  }) as unknown as Response;

beforeEach(() => {
  jest.clearAllMocks();
});

it("成功時は success:true を返す", async () => {
  mockFetch.mockResolvedValue({ ok: true, status: 202 } as unknown as Response);

  await expect(createReport(baseParams)).resolves.toEqual({ success: true });
});

it("ユーザー API キーは x-user-api-key ヘッダーで送り、リダイレクト先へは転送しない", async () => {
  mockFetch.mockResolvedValue({ ok: true, status: 202 } as unknown as Response);

  await createReport({ ...baseParams, userApiKey: "user-key" });

  const [url, options] = mockFetch.mock.calls[0];
  expect(url).toBe("http://localhost:8000/admin/reports");
  expect(options.headers["x-user-api-key"]).toBe("user-key");
  expect(options.redirect).toBe("error");
  expect(options.body).not.toContain("user-key");
});

it("既存IDで 409 が返ったら重複を伝えるメッセージを返す", async () => {
  mockFetch.mockResolvedValue(errorResponse(409, "Conflict", { detail: "Report already exists" }));

  const result = await createReport(baseParams);

  expect(result).toEqual({ success: false, error: "同じIDのレポートが既に存在します。別のIDを指定してください" });
});

it("API が返した detail 文字列をエラーとして返す", async () => {
  mockFetch.mockResolvedValue(errorResponse(400, "Bad Request", { detail: "Invalid slug format" }));

  const result = await createReport(baseParams);

  expect(result).toEqual({ success: false, error: "Invalid slug format" });
});

it("422 の detail 配列を項目と理由に整形して返す", async () => {
  mockFetch.mockResolvedValue(
    errorResponse(422, "Unprocessable Entity", {
      detail: [
        { loc: ["body", "cluster"], msg: "Field required", type: "missing" },
        { loc: ["body", "workers"], msg: "Input should be a valid integer", type: "int_parsing" },
      ],
    }),
  );

  const result = await createReport(baseParams);

  expect(result).toEqual({
    success: false,
    error: "body.cluster: Field required / body.workers: Input should be a valid integer",
  });
});

it("本文が JSON でなければ statusText にフォールバックする", async () => {
  mockFetch.mockResolvedValue({
    ok: false,
    status: 502,
    statusText: "Bad Gateway",
    json: jest.fn().mockRejectedValue(new SyntaxError("Unexpected token")),
  } as unknown as Response);

  const result = await createReport(baseParams);

  expect(result).toEqual({ success: false, error: "Bad Gateway" });
});
