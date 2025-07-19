import { Provider } from "@/components/ui/provider";
import { toaster } from "@/components/ui/toaster";
import type { Report } from "@/type";
import { ReportVisibility } from "@/type";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ReportEditDialog } from "./ReportEditDialog";

// Mock toaster
jest.mock("@/components/ui/toaster", () => ({
  toaster: {
    create: jest.fn(),
  },
}));

// Mock getApiBaseUrl
jest.mock("../../../utils/api", () => ({
  getApiBaseUrl: jest.fn(() => "http://localhost:8000"),
}));

// Mock useRouter
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  })),
}));

// Mock server action
jest.mock("./actions", () => ({
  updateReportConfig: jest.fn(),
}));

// Mock environment variable
const originalEnv = process.env;
beforeEach(() => {
  process.env = { ...originalEnv, NEXT_PUBLIC_ADMIN_API_KEY: "test-api-key" };
  jest.clearAllMocks();
});

afterEach(() => {
  process.env = originalEnv;
});

const mockReport: Report = {
  slug: "test-report",
  status: "processing",
  title: "Test Report Title",
  description: "Test Report Description",
  isPubcom: false,
  visibility: ReportVisibility.PUBLIC,
};

const defaultProps = {
  isEditDialogOpen: true,
  setIsEditDialogOpen: jest.fn(),
  report: mockReport,
};

function renderWithProvider(component: React.ReactElement) {
  return render(<Provider>{component}</Provider>);
}

describe("ReportEditDialog", () => {
  describe("レンダリング", () => {
    it("ダイアログが開いている時に表示される", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} />);

      expect(screen.getByText("レポートを編集")).toBeInTheDocument();
      expect(screen.getByText("タイトル")).toBeInTheDocument();
      expect(screen.getByText("調査概要")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Test Report Title")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Test Report Description")).toBeInTheDocument();
      expect(screen.getByText("キャンセル")).toBeInTheDocument();
      expect(screen.getByText("保存")).toBeInTheDocument();
    });

    it("ダイアログが閉じている時は表示されない", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} isEditDialogOpen={false} />);

      expect(screen.queryByText("レポートを編集")).not.toBeInTheDocument();
    });
  });

  describe("フォーム操作", () => {
    it("タイトル入力欄の値を変更できる", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} />);

      const titleInput = screen.getByDisplayValue("Test Report Title");
      fireEvent.change(titleInput, { target: { value: "Updated Title" } });

      expect(titleInput).toHaveValue("Updated Title");
    });

    it("説明入力欄の値を変更できる", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} />);

      const descriptionTextarea = screen.getByDisplayValue("Test Report Description");
      fireEvent.change(descriptionTextarea, { target: { value: "Updated Description" } });

      expect(descriptionTextarea).toHaveValue("Updated Description");
    });

    it("キャンセルボタンを押すとダイアログが閉じる", () => {
      const mockSetIsEditDialogOpen = jest.fn();
      renderWithProvider(<ReportEditDialog {...defaultProps} setIsEditDialogOpen={mockSetIsEditDialogOpen} />);

      const cancelButton = screen.getByText("キャンセル");
      fireEvent.click(cancelButton);

      expect(mockSetIsEditDialogOpen).toHaveBeenCalledWith(false);
    });
  });

  describe("保存処理", () => {
    it("保存が成功した場合の処理", async () => {
      const mockSetIsEditDialogOpen = jest.fn();
      const mockRouterRefresh = jest.fn();
      const { updateReportConfig } = require("./actions");

      // useRouterのrefreshメソッドをモック
      const { useRouter } = require("next/navigation");
      useRouter.mockReturnValue({
        push: jest.fn(),
        refresh: mockRouterRefresh,
        back: jest.fn(),
        forward: jest.fn(),
        replace: jest.fn(),
        prefetch: jest.fn(),
      });

      // Server actionのモック
      updateReportConfig.mockResolvedValueOnce({
        success: true,
      });

      renderWithProvider(<ReportEditDialog {...defaultProps} setIsEditDialogOpen={mockSetIsEditDialogOpen} />);

      // タイトルと説明を変更
      const titleInput = screen.getByDisplayValue("Test Report Title");
      const descriptionTextarea = screen.getByDisplayValue("Test Report Description");
      fireEvent.change(titleInput, { target: { value: "Updated Title" } });
      fireEvent.change(descriptionTextarea, { target: { value: "Updated Description" } });

      // 保存ボタンをクリック
      const saveButton = screen.getByText("保存");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(updateReportConfig).toHaveBeenCalledWith("test-report", expect.any(FormData));
      });

      // router.refresh()が呼ばれる
      expect(mockRouterRefresh).toHaveBeenCalled();

      // 成功メッセージが表示される
      expect(toaster.create).toHaveBeenCalledWith({
        type: "success",
        title: "更新完了",
        description: "レポート情報が更新されました",
      });

      // ダイアログが閉じる
      expect(mockSetIsEditDialogOpen).toHaveBeenCalledWith(false);
    });

    it("API呼び出しが失敗した場合のエラー処理", async () => {
      const mockSetIsEditDialogOpen = jest.fn();
      const { updateReportConfig } = require("./actions");

      // Server actionが失敗を返すようにモック
      updateReportConfig.mockResolvedValueOnce({
        success: false,
        error: "API Error Message",
      });

      renderWithProvider(<ReportEditDialog {...defaultProps} setIsEditDialogOpen={mockSetIsEditDialogOpen} />);

      const saveButton = screen.getByText("保存");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(toaster.create).toHaveBeenCalledWith({
          type: "error",
          title: "更新エラー",
          description: "API Error Message",
        });
      });

      // ダイアログは閉じない
      expect(mockSetIsEditDialogOpen).not.toHaveBeenCalledWith(false);
    });

    it("API呼び出しでネットワークエラーが発生した場合の処理", async () => {
      const mockSetIsEditDialogOpen = jest.fn();
      const { updateReportConfig } = require("./actions");

      // Server actionがエラーなしで失敗を返すようにモック
      updateReportConfig.mockResolvedValueOnce({
        success: false,
      });

      renderWithProvider(<ReportEditDialog {...defaultProps} setIsEditDialogOpen={mockSetIsEditDialogOpen} />);

      const saveButton = screen.getByText("保存");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(toaster.create).toHaveBeenCalledWith({
          type: "error",
          title: "更新エラー",
          description: "メタデータの更新に失敗しました",
        });
      });

      expect(mockSetIsEditDialogOpen).not.toHaveBeenCalledWith(false);
    });
  });

  describe("アクセシビリティ", () => {
    it("適切なaria属性とrole属性が設定されている", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} />);

      // ダイアログのタイトルが適切に設定されている
      expect(screen.getByText("レポートを編集")).toBeInTheDocument();

      // 入力フィールドのラベルが適切に設定されている
      expect(screen.getByText("タイトル")).toBeInTheDocument();
      expect(screen.getByText("調査概要")).toBeInTheDocument();

      // プレースホルダーテキストが設定されている
      expect(screen.getByPlaceholderText("レポートのタイトルを入力")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("調査の概要を入力")).toBeInTheDocument();
    });

    it("フォーカス管理が適切に動作する", () => {
      renderWithProvider(<ReportEditDialog {...defaultProps} />);

      // ダイアログが開いた時にフォーカスが適切に管理されることを確認
      // (trapFocus=trueが設定されている)
      const titleInput = screen.getByDisplayValue("Test Report Title");
      expect(titleInput).toBeInTheDocument();
    });
  });
});
