import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps, ReactNode } from "react";
import { parseCsv } from "../parseCsv";
import { CsvFileTab } from "./CsvFileTab";

jest.mock("lucide-react", () => ({ DownloadIcon: () => null }));
jest.mock("../parseCsv", () => ({ parseCsv: jest.fn() }));
jest.mock("@chakra-ui/react", () => ({
  Box: ({ children, role }: { children: ReactNode; role?: string }) => <div role={role}>{children}</div>,
  VStack: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Tabs: { Content: ({ children }: { children: ReactNode }) => <div>{children}</div> },
}));
jest.mock("@/components/ui/file-upload", () => ({
  FileUploadRoot: ({
    children,
    onFileChange,
  }: {
    children: ReactNode;
    onFileChange: (event: { acceptedFiles: File[] }) => Promise<void>;
  }) => (
    <div>
      <input
        aria-label="CSV"
        type="file"
        onChange={(e) => void onFileChange({ acceptedFiles: Array.from(e.target.files ?? []) })}
      />
      {children}
    </div>
  ),
  FileUploadDropzone: () => null,
  FileUploadList: ({ onRemove }: { onRemove: () => void }) => (
    <button type="button" onClick={onRemove}>
      削除
    </button>
  ),
}));
jest.mock("./AttributeColumnsSelector", () => ({ AttributeColumnsSelector: () => null }));
jest.mock("./ClusterSettingsSection", () => ({ ClusterSettingsSection: () => null }));
jest.mock("./CommentColumnSelector", () => ({ CommentColumnSelector: () => null }));

function setup() {
  const props: ComponentProps<typeof CsvFileTab> = {
    csv: null,
    csvColumns: ["old"],
    selectedCommentColumn: "old",
    selectedAttributeColumns: ["age"],
    setCsv: jest.fn(),
    setCsvColumns: jest.fn(),
    setSelectedCommentColumn: jest.fn(),
    setSelectedAttributeColumns: jest.fn(),
    clusterSettings: {
      clusterLv1: 5,
      clusterLv2: 50,
      recommendedClusters: null,
      autoAdjusted: false,
      calculateRecommendedClusters: jest.fn(),
      setRecommended: jest.fn(),
      handleLv1Change: jest.fn(),
      handleLv2Change: jest.fn(),
      resetClusterSettings: jest.fn(),
    },
  };
  render(<CsvFileTab {...props} />);
  return props;
}
const choose = (name: string) => {
  const file = new File(["csv"], name, { type: "text/csv" });
  fireEvent.change(screen.getByLabelText("CSV"), { target: { files: [file] } });
  return file;
};
afterEach(() => jest.resetAllMocks());

it("読み込み失敗の説明を表示し、古い入力を破棄してから再選択できる", async () => {
  jest.mocked(parseCsv).mockRejectedValueOnce(new Error("データの1件目: ヘッダーより列が多くなっています。"));
  const props = setup();
  choose("broken.csv");
  expect(await screen.findByRole("alert")).toHaveTextContent("列が多く");
  expect(props.setCsv).toHaveBeenLastCalledWith(null);
  expect(props.setCsvColumns).toHaveBeenLastCalledWith([]);
  expect(props.setSelectedAttributeColumns).toHaveBeenLastCalledWith([]);
  jest.mocked(parseCsv).mockResolvedValueOnce([{ id: "1", comment: "意見" }]);
  const corrected = choose("corrected.csv");
  await waitFor(() => expect(props.setCsv).toHaveBeenLastCalledWith(corrected));
  expect(screen.queryByRole("alert")).toBeNull();
});

it("削除後に遅れて終わった読み込みから入力を復活させない", async () => {
  let finish!: (rows: Awaited<ReturnType<typeof parseCsv>>) => void;
  jest.mocked(parseCsv).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    }),
  );
  const props = setup();
  choose("slow.csv");
  fireEvent.click(screen.getByText("削除"));
  await act(async () => finish([{ id: "1", comment: "意見" }]));
  expect(props.setCsv).toHaveBeenLastCalledWith(null);
  expect(props.clusterSettings.setRecommended).not.toHaveBeenCalled();
});
