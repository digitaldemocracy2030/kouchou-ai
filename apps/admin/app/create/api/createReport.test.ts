import { getApiBaseUrl } from "@/app/utils/api";
import { createReport } from "./createReport";

jest.mock("@/app/utils/api", () => ({
  getApiBaseUrl: jest.fn(),
}));

global.fetch = jest.fn();

const baseParams = {
  input: "existing-slug",
  question: "q",
  intro: "i",
  comments: [],
  cluster: [3, 6] as [number, number],
  provider: "openai",
  model: "gpt-4o-mini",
  workers: 1,
  prompt: { extraction: "ex", initialLabelling: "il", mergeLabelling: "ml", overview: "ov" },
  analysis_mode: "hierarchical",
  is_pubcom: false,
  inputType: "file",
  is_embedded_at_local: false,
  enable_source_link: false,
};

describe("createReport", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (getApiBaseUrl as jest.Mock).mockReturnValue("https://api.example.com");
  });

  it("成功時は success:true を返す", async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({ ok: true, status: 202 });

    await expect(createReport(baseParams)).resolves.toEqual({ success: true });
  });

  it("既存IDで 409 が返ったら重複を伝えるメッセージを返す", async () => {
    (fetch as jest.Mock).mockResolvedValueOnce({ ok: false, status: 409, statusText: "Conflict" });

    const result = await createReport(baseParams);

    expect(result.success).toBe(false);
    expect(result.error).toBe("同じIDのレポートが既に存在します。別のIDを指定してください");
  });
});
