import type { ClusterResponse, Report } from "@/type";
import { ReportVisibility } from "@/type";
import { ChakraProvider, createSystem, defaultConfig } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ClusterEditDialog } from "./ClusterEditDialog";

// Mock the toaster
jest.mock("@/components/ui/toaster", () => ({
  toaster: {
    create: jest.fn(),
  },
}));

// Mock the server actions
jest.mock("./actions", () => ({
  fetchClusters: jest.fn(),
  updateCluster: jest.fn(),
}));

// Mock the API utility
jest.mock("@/app/utils/api", () => ({
  getApiBaseUrl: jest.fn(() => "http://localhost:8000"),
}));

// Mock environment variables
process.env.NEXT_PUBLIC_ADMIN_API_KEY = "test-api-key";

const mockReport: Report = {
  slug: "test-report",
  status: "processing",
  title: "Test Report",
  description: "Test Description",
  isPubcom: false,
  visibility: ReportVisibility.PUBLIC,
};

const mockClusters: ClusterResponse[] = [
  {
    level: 1,
    id: "cluster-1",
    label: "Test Cluster 1",
    description: "Description for cluster 1",
    value: 10,
    parent: null,
    density: 0.8,
    density_rank: 1,
    density_rank_percentile: 90,
  },
  {
    level: 1,
    id: "cluster-2",
    label: "Test Cluster 2",
    description: "Description for cluster 2",
    value: 5,
    parent: null,
    density: 0.6,
    density_rank: 2,
    density_rank_percentile: 70,
  },
  {
    level: 2,
    id: "cluster-3",
    label: "Test Cluster 3",
    description: "Description for cluster 3",
    value: 3,
    parent: "cluster-1",
    density: 0.4,
    density_rank: 3,
    density_rank_percentile: 50,
  },
];

const system = createSystem(defaultConfig);

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <ChakraProvider value={system}>{children}</ChakraProvider>
);

describe("ClusterEditDialog", () => {
  const mockOnClose = jest.fn();
  const mockFetchClusters = require("./actions").fetchClusters;
  const mockUpdateCluster = require("./actions").updateCluster;

  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchClusters.mockResolvedValue({
      success: true,
      clusters: mockClusters,
    });
    mockUpdateCluster.mockResolvedValue({
      success: true,
    });
  });

  it("ダイアログが開いているときにレンダリングされる", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("意見グループを編集")).toBeInTheDocument();
    });
  });

  it("ダイアログが閉じているときはレンダリングされない", () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={false} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    expect(screen.queryByText("意見グループを編集")).not.toBeInTheDocument();
  });

  it("ダイアログが開かれたときにクラスタ一覧を取得する", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(mockFetchClusters).toHaveBeenCalledWith("test-report");
    });
  });

  it("利用可能な階層レベルが表示される", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue("第1階層")).toBeInTheDocument();
    });
  });

  it("選択された階層のクラスタが表示される", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      const titleInput = screen.getByPlaceholderText("タイトルを入力");
      expect(titleInput).toHaveValue("Test Cluster 1");
    });
  });

  it("クラスタが選択されたときにフォームフィールドが更新される", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      const titleInput = screen.getByPlaceholderText("タイトルを入力");
      const descriptionTextarea = screen.getByPlaceholderText("説明を入力");
      expect(titleInput).toHaveValue("Test Cluster 1");
      expect(descriptionTextarea).toHaveValue("Description for cluster 1");
    });
  });

  it("クラスタのタイトルと説明を編集できる", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    const user = userEvent.setup();

    const titleInput = await screen.findByPlaceholderText("タイトルを入力");
    const descriptionTextarea = await screen.findByPlaceholderText("説明を入力");

    await user.clear(titleInput);
    await user.type(titleInput, "Updated Title");
    await user.clear(descriptionTextarea);
    await user.type(descriptionTextarea, "Updated Description");

    expect(titleInput).toHaveValue("Updated Title");
    expect(descriptionTextarea).toHaveValue("Updated Description");
  });

  it("保存ボタンがクリックされたときに変更が送信される", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    const user = userEvent.setup();

    const titleInput = await screen.findByPlaceholderText("タイトルを入力");
    await user.clear(titleInput);
    await user.type(titleInput, "Updated Title");

    const saveButton = screen.getByText("保存");
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateCluster).toHaveBeenCalledWith("test-report", expect.any(FormData));
    });

    // Verify FormData contents
    const formDataCall = mockUpdateCluster.mock.calls[0][1] as FormData;
    expect(formDataCall.get("id")).toBe("cluster-1");
    expect(formDataCall.get("label")).toBe("Updated Title");
    expect(formDataCall.get("description")).toBe("Description for cluster 1");
  });

  it("キャンセルボタンがクリックされたときにダイアログが閉じる", async () => {
    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("キャンセル")).toBeInTheDocument();
    });

    const cancelButton = screen.getByText("キャンセル");
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("クラスタが存在しないときはダイアログが表示されない", async () => {
    mockFetchClusters.mockResolvedValue({
      success: true,
      clusters: [],
    });

    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.queryByText("意見グループを編集")).not.toBeInTheDocument();
    });
  });

  it("クラスタ取得時のAPIエラーを処理する", async () => {
    const mockToaster = require("@/components/ui/toaster").toaster;
    mockFetchClusters.mockResolvedValue({
      success: false,
      error: "クラスタ一覧の取得に失敗しました",
    });

    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(mockToaster.create).toHaveBeenCalledWith({
        type: "error",
        title: "エラー",
        description: "クラスタ一覧の取得に失敗しました。",
      });
    });
  });

  it("クラスタ更新時のAPIエラーを処理する", async () => {
    const mockToaster = require("@/components/ui/toaster").toaster;
    mockUpdateCluster.mockResolvedValue({
      success: false,
      error: "入力データが不正です: Invalid data",
    });

    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    const user = userEvent.setup();

    const saveButton = await screen.findByText("保存");
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockToaster.create).toHaveBeenCalledWith({
        type: "error",
        title: "更新エラー",
        description: "入力データが不正です: Invalid data",
      });
    });
  });

  it("クラスタが選択されている場合のみ編集フォームが表示される", async () => {
    mockFetchClusters.mockResolvedValue({
      success: true,
      clusters: [],
    });

    render(
      <TestWrapper>
        <ClusterEditDialog report={mockReport} isOpen={true} setIsClusterEditDialogOpen={mockOnClose} />
      </TestWrapper>,
    );

    await waitFor(() => {
      expect(screen.queryByText("意見グループの編集")).not.toBeInTheDocument();
    });
  });
});
