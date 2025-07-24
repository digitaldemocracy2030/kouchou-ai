import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EnvironmentCheckDialog } from "./EnvironmentCheckDialog";
import { verifyChatGptApiKey } from "./verifyChatGptApiKey";

// test時のimportエラーを防止するために、lucide-reactをモック化
jest.mock("lucide-react", () => ({
  SquareArrowOutUpRight: () => <div data-testid="arrow-icon" />,
}));

// verifyChatGptApiKeyをモック化
jest.mock("./verifyChatGptApiKey");
const mockVerifyChatGptApiKey = verifyChatGptApiKey as jest.MockedFunction<typeof verifyChatGptApiKey>;

// crypto.randomUUIDをモック化
const mockUUID = "test-uuid-123";
Object.defineProperty(global, "crypto", {
  value: {
    randomUUID: jest.fn(() => mockUUID),
  },
});

// テスト用のChakraUIラッパーコンポーネント
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <ChakraProvider value={system}>{children}</ChakraProvider>
);

describe("EnvironmentCheckDialog", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("初期状態でトリガーボタンが表示される", () => {
    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    expect(screen.getByRole("button", { name: /API接続チェック/i })).toBeInTheDocument();
  });

  it("トリガーボタンをクリックすると初期状態のダイアログが開く", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({ result: null, error: false });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    expect(await screen.findByText("APIキー設定とデポジット残高を確認します。")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "チェックする" })).toBeInTheDocument();
  });

  it("チェックボタンをクリックするとAPIが呼び出される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({ result: null, error: false });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    await waitFor(() => {
      expect(mockVerifyChatGptApiKey).toHaveBeenCalledTimes(1);
    });
  });

  it("API接続が成功した場合に成功メッセージが表示される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({
      result: {
        success: true,
        message: "接続成功",
        available_models: ["gpt-4"],
      },
      error: false,
    });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    expect(await screen.findByText(/正しく接続されています/)).toBeInTheDocument();
    expect(await screen.findByText(/このままレポートを作成いただけます/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "閉じる" })).toBeInTheDocument();
  });

  it("認証エラーの場合にエラーメッセージが表示される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({
      result: {
        success: false,
        message: "認証エラー",
        error_type: "authentication_error",
        error_detail: "Invalid API key",
      },
      error: true,
    });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    expect(await screen.findByText(/エラーが見つかりました。/)).toBeInTheDocument();
    expect(
      await screen.findByText(
        /APIキーが無効または期限切れです。.envファイルを確認し修正してください。APIキーを改めて取得し直した場合も再設定が必要です。/,
      ),
    ).toBeInTheDocument();
  });

  it("クォータ不足エラーの場合にエラーメッセージが表示される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({
      result: {
        success: false,
        message: "クォータ不足",
        error_type: "insufficient_quota",
        error_detail: "Insufficient quota",
      },
      error: true,
    });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    expect(await screen.findByText(/エラーが見つかりました。/)).toBeInTheDocument();
    expect(await screen.findByText(/デポジット残高が不足しています。チャージしてください。/)).toBeInTheDocument();
  });

  it("レート制限エラーの場合にエラーメッセージが表示される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({
      result: {
        success: false,
        message: "レート制限",
        error_type: "rate_limit_error",
        error_detail: "Rate limit exceeded",
      },
      error: true,
    });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    expect(await screen.findByText(/エラーが見つかりました/)).toBeInTheDocument();
    expect(
      await screen.findByText(/APIのレート制限に達しました。時間をおいて再度お試しください。/),
    ).toBeInTheDocument();
  });

  it("不明なエラーの場合にエラーメッセージが表示される", async () => {
    mockVerifyChatGptApiKey.mockResolvedValue({
      result: {
        success: false,
        message: "不明なエラー",
        error_type: "unknown_error",
        error_detail: "Unknown error occurred",
      },
      error: true,
    });

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    const checkButton = await screen.findByRole("button", { name: "チェックする" });
    userEvent.click(checkButton);

    expect(await screen.findByText(/エラーが見つかりました/)).toBeInTheDocument();
    expect(
      await screen.findByText(/不明なエラーが発生しました。APIの設定や接続を再確認してください。/),
    ).toBeInTheDocument();
  });

  it("ダイアログを閉じるとUUIDがリセットされる", async () => {
    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    await waitFor(() => {
      const closeButton = screen.getByRole("button", { name: "Close" });
      userEvent.click(closeButton);
    });

    // crypto.randomUUIDが再度呼び出されることを確認
    expect(global.crypto.randomUUID).toHaveBeenCalledTimes(1);
  });

  it("チェック中にローディング状態が表示される", async () => {
    // Promiseを解決せずに保留状態にする
    let resolvePromise: (value: { result: null; error: boolean }) => void = () => {};
    const pendingPromise = new Promise<{ result: null; error: boolean }>((resolve) => {
      resolvePromise = resolve;
    });
    mockVerifyChatGptApiKey.mockReturnValue(pendingPromise);

    render(
      <TestWrapper>
        <EnvironmentCheckDialog />
      </TestWrapper>,
    );

    userEvent.click(screen.getByRole("button", { name: /API接続チェック/i }));

    await waitFor(() => {
      const checkButton = screen.getByRole("button", { name: "チェックする" });
      userEvent.click(checkButton);
    });

    // ローディング状態を確認
    expect(await screen.findByRole("button", { name: "チェックする" })).toBeDisabled();

    // Promiseを解決してテストを終了
    resolvePromise({ result: null, error: false });
  });
});
