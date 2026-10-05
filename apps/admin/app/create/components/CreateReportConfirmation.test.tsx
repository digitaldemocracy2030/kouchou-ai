import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreateReportConfirmation, type PreparedReport } from "./CreateReportConfirmation";
import { verifyApiKey } from "./EnvironmentCheckDialog/verifyApiKey";

jest.mock("./EnvironmentCheckDialog/verifyApiKey", () => ({ verifyApiKey: jest.fn() }));
const verify = jest.mocked(verifyApiKey);
const prepared: PreparedReport = {
  request: {
    input: "test",
    question: "調査タイトル",
    intro: "",
    comments: [
      { id: "1", comment: "意見" },
      { id: "2", comment: " " },
    ],
    cluster: [2, 5],
    provider: "openai",
    model: "gpt-4o-mini",
    workers: 1,
    prompt: { extraction: "p", initialLabelling: "p", mergeLabelling: "p", overview: "p" },
    is_pubcom: false,
    inputType: "file",
    is_embedded_at_local: false,
    enable_source_link: false,
    userApiKey: "test-key",
  },
  commentColumn: "回答",
  attributeColumns: ["年代", "地域"],
};
function mount(data = prepared, onCancel = jest.fn(), onConfirm = jest.fn()) {
  return render(
    <ChakraProvider value={system}>
      <CreateReportConfirmation prepared={data} loading={false} onCancel={onCancel} onConfirm={onConfirm} />
    </ChakraProvider>,
  );
}
beforeEach(() => jest.clearAllMocks());

it("入力内容と警告を表示し、開いた時点ではAPIを呼ばない", async () => {
  const confirm = jest.fn();
  const cancel = jest.fn();
  mount(prepared, cancel, confirm);
  expect(await screen.findByRole("dialog")).toBeVisible();
  expect(screen.getByText("コメント列：回答")).toBeVisible();
  expect(screen.getByText("コメント件数：2件（非空：1件）")).toBeVisible();
  expect(screen.getByText("属性列：年代、地域")).toBeVisible();
  expect(screen.getByText(/非空コメント数が第2階層/)).toBeVisible();
  expect(screen.getByText("費用：目安なし")).toBeVisible();
  expect(verify).not.toHaveBeenCalled();
  expect(confirm).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "設定に戻る" }));
  expect(cancel).toHaveBeenCalledTimes(1);
  expect(confirm).not.toHaveBeenCalled();
});

it.each([
  ["authentication_error", "認証エラー"],
  ["insufficient_quota", "残高不足"],
  ["rate_limit_error", "rate limit"],
  ["unknown_error", "不明なエラー"],
] as const)("APIの%sを表示する", async (error_type, text) => {
  verify.mockResolvedValue({ result: { success: false, message: "error", error_type }, error: true });
  mount();
  await userEvent.click(await screen.findByRole("button", { name: "API接続を確認する" }));
  expect(await screen.findByText(new RegExp(`^${text}`))).toBeVisible();
  expect(verify).toHaveBeenCalledWith("openai", "test-key", prepared.request.model, undefined);
});

it("接続確認の成功と明示した作成操作を扱う", async () => {
  verify.mockResolvedValue({ result: { success: true, message: "ok" }, error: false });
  const confirm = jest.fn();
  mount(prepared, jest.fn(), confirm);
  await userEvent.click(await screen.findByRole("button", { name: "API接続を確認する" }));
  await userEvent.click(await screen.findByRole("button", { name: "この内容で作成を開始" }));
  expect(confirm).toHaveBeenCalledTimes(1);
});

it("応答にsuccessがない場合は成功扱いしない", async () => {
  verify.mockResolvedValue({ result: null, error: false });
  mount();
  await userEvent.click(await screen.findByRole("button", { name: "API接続を確認する" }));
  expect(await screen.findByText(/^不明なエラー/)).toBeVisible();
});

it("確認中は作成できず、キャンセル後の再表示では結果を引き継がない", async () => {
  let resolve!: (result: Awaited<ReturnType<typeof verifyApiKey>>) => void;
  verify.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const view = mount();
  await userEvent.click(await screen.findByRole("button", { name: "API接続を確認する" }));
  expect(screen.getByRole("button", { name: "未確認のまま作成を開始" })).toBeDisabled();
  resolve({ result: { success: true, message: "ok" }, error: false });
  await waitFor(() => expect(screen.getByText(/^OK/)).toBeVisible());
  view.unmount();
  mount();
  expect(await screen.findByText("未確認")).toBeVisible();
});

it("Azureではサーバー設定、localでは接続確認を表示し、空入力は開始させない", async () => {
  const view = mount({ ...prepared, request: { ...prepared.request, provider: "azure", model: "old-model" } });
  expect(await screen.findByText("AI：azure / サーバー設定を使用")).toBeVisible();
  expect(screen.queryByText(/old-model/)).not.toBeInTheDocument();
  view.unmount();
  mount({ ...prepared, request: { ...prepared.request, provider: "local", comments: [] } });
  expect(await screen.findByText(/接続先：/)).toBeVisible();
  expect(screen.getByRole("button", { name: "API接続を確認する" })).toBeVisible();
  expect(screen.getByRole("button", { name: "未確認のまま作成を開始" })).toBeDisabled();
});

it.each(["local", "openrouter", "azure"] as const)("%sの選択設定を接続確認へ渡す", async (provider) => {
  verify.mockResolvedValue({ result: { success: true, message: "ok" }, error: false });
  mount({
    ...prepared,
    request: { ...prepared.request, provider, model: "selected-model", local_llm_address: "localhost:1234" },
  });
  await userEvent.click(await screen.findByRole("button", { name: "API接続を確認する" }));
  expect(verify).toHaveBeenCalledWith(provider, "test-key", "selected-model", "localhost:1234");
  expect(await screen.findByText(/^OK/)).toBeVisible();
});

it("Azureの接続失敗ではAPIバージョンと設定項目を案内する", async () => {
  verify.mockResolvedValue({ result: null, error: true });
  mount({ ...prepared, request: { ...prepared.request, provider: "azure" } }, jest.fn(), jest.fn());
  await userEvent.click(screen.getByRole("button", { name: "API接続を確認する" }));
  expect(
    await screen.findByText(/AZURE_CHATCOMPLETION_VERSIONにはモデルのバージョンではなくAPIバージョン/),
  ).toBeInTheDocument();
});
