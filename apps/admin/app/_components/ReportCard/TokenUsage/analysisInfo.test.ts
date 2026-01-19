import type { Report } from "@/type";
import { ReportVisibility } from "@/type";
import { analysisInfo } from "./analysisInfo";

describe("analysisInfo", () => {
  const baseReport: Report = {
    slug: "test-report",
    status: "processing",
    title: "Test Report",
    description: "Test Description",
    isPubcom: false,
    visibility: ReportVisibility.PUBLIC,
  };

  describe("入力・出力トークン情報がある場合", () => {
    it("正しく詳細なトークン情報を返す", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
        tokenUsageOutput: 500,
        tokenUsage: 1500,
        estimatedCost: 0.123456,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result).toEqual({
        hasInput: true,
        hasTotal: true,
        estimatedCost: "$0.123456",
        model: "OpenAI gpt-4",
        tokenUsageInput: "1,000",
        tokenUsageOutput: "500",
      });
    });

    it("プロバイダーまたはモデルが欠けている場合はnullを返す", () => {
      const reportWithoutProvider: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
        tokenUsageOutput: 500,
        model: "gpt-4",
      };

      const result = analysisInfo(reportWithoutProvider);

      expect(result.model).toBeNull();

      const reportWithoutModel: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
        tokenUsageOutput: 500,
        provider: "OpenAI",
      };

      const result2 = analysisInfo(reportWithoutModel);

      expect(result2.model).toBeNull();
    });
  });

  describe("合計トークン情報のみある場合", () => {
    it("合計トークン情報を詳細なしで返す", () => {
      const report: Report = {
        ...baseReport,
        tokenUsage: 1500,
        estimatedCost: 0.123456,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result).toEqual({
        hasInput: false,
        hasTotal: true,
        estimatedCost: "$0.123456",
        model: "OpenAI gpt-4",
        tokenUsageTotal: "1,500 (詳細なし)",
      });
    });
  });

  describe("トークン情報がない場合", () => {
    it("情報なしとして返す", () => {
      const report: Report = {
        ...baseReport,
        estimatedCost: 0.123456,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result).toEqual({
        hasInput: false,
        hasTotal: false,
        estimatedCost: "$0.123456",
        model: "OpenAI gpt-4",
        tokenUsageTotal: "情報なし",
      });
    });
  });

  describe("推定コスト処理", () => {
    it("推定コストがない場合は「情報なし」を返す", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
        tokenUsageOutput: 500,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result.estimatedCost).toBe("情報なし");
    });

    it("推定コストが0の場合は正しくフォーマットする", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
        tokenUsageOutput: 500,
        estimatedCost: 0,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result.estimatedCost).toBe("$0.000000");
    });
  });

  describe("数値フォーマット", () => {
    it("大きな数値を正しくフォーマットする", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageInput: 123456,
        tokenUsageOutput: 654321,
        tokenUsage: 777777,
        provider: "OpenAI",
        model: "gpt-4",
      };

      const result = analysisInfo(report);

      expect(result.tokenUsageInput).toBe("123,456");
      expect(result.tokenUsageOutput).toBe("654,321");
    });
  });

  describe("エッジケース", () => {
    it("入力トークンのみある場合は詳細情報なしとして扱う", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageInput: 1000,
      };

      const result = analysisInfo(report);

      expect(result.hasInput).toBe(false);
      expect(result.tokenUsageTotal).toBe("情報なし");
    });

    it("出力トークンのみある場合は詳細情報なしとして扱う", () => {
      const report: Report = {
        ...baseReport,
        tokenUsageOutput: 500,
      };

      const result = analysisInfo(report);

      expect(result.hasInput).toBe(false);
      expect(result.tokenUsageTotal).toBe("情報なし");
    });
  });
});
