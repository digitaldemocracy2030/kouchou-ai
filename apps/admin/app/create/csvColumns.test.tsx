import { system } from "@/components/theme/system";
import { ChakraProvider, Tabs } from "@chakra-ui/react";
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { CsvFileTab } from "./components/CsvFileTab";
import { useClusterSettings } from "./hooks/useClusterSettings";
import { useInputData } from "./hooks/useInputData";
import { parseCsv } from "./parseCsv";
import { getBestCommentColumn } from "./utils/columnScorer";

jest.mock("./parseCsv", () => {
  const actual = jest.requireActual("./parseCsv");
  return { ...actual, parseCsv: jest.fn(actual.parseCsv) };
});
jest.mock("lucide-react", () => ({ DownloadIcon: () => null }));
jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));
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
  FileUploadList: () => null,
}));
jest.mock("./components/ClusterSettingsSection", () => ({ ClusterSettingsSection: () => null }));

const actualParseCsv: typeof parseCsv = jest.requireActual("./parseCsv").parseCsv;

/** コメント列名が既定リストに無く、回答が短い CSV（合成 id の "csv-N" の方が長い） */
const shortAnswerCsv = () =>
  new File([["回答", ...Array.from({ length: 30 }, (_, i) => ["はい", "いいえ"][i % 2])].join("\n")], "short.csv", {
    type: "text/csv",
  });

/** 呼ばれた parseCsv がすべて終わるまで待つ */
async function settleParses() {
  for (let i = 0; i < 3; i++) {
    await act(async () => {
      await Promise.allSettled(jest.mocked(parseCsv).mock.results.map((r) => r.value));
    });
  }
}

let latest: ReturnType<typeof useInputData>;
/** page.tsx と同じ配線で CsvFileTab と useInputData をつなぐ */
function Harness() {
  const clusterSettings = useClusterSettings();
  const inputData = useInputData(clusterSettings.setRecommended);
  latest = inputData;
  return (
    <Tabs.Root value="file">
      <CsvFileTab
        csv={inputData.csv}
        setCsv={(file) => inputData.setCsv(file)}
        csvColumns={inputData.csvColumns}
        setCsvColumns={inputData.setCsvColumns}
        selectedCommentColumn={inputData.selectedCommentColumn}
        setSelectedCommentColumn={inputData.setSelectedCommentColumn}
        selectedAttributeColumns={inputData.selectedAttributeColumns}
        setSelectedAttributeColumns={inputData.setSelectedAttributeColumns}
        clusterSettings={clusterSettings}
      />
    </Tabs.Root>
  );
}

beforeEach(() => {
  jest.mocked(parseCsv).mockReset();
  jest.mocked(parseCsv).mockImplementation(actualParseCsv);
});

it("CSV を選ぶと 1 回だけ解析し、合成 id 列を候補にも自動選択にも入れない", async () => {
  render(
    <ChakraProvider value={system}>
      <Harness />
    </ChakraProvider>,
  );
  const file = shortAnswerCsv();
  fireEvent.change(screen.getByLabelText("CSV"), { target: { files: [file] } });
  await waitFor(() => expect(latest.csv).toBe(file));
  await settleParses();

  expect(parseCsv).toHaveBeenCalledTimes(1);
  expect(latest.csvColumns).toEqual(["回答"]);
  expect(latest.selectedCommentColumn).toBe("回答");
  const options = Array.from(document.querySelectorAll("select option")).map((o) => (o as HTMLOptionElement).value);
  expect(options).not.toContain("id");
});

it("CSV タブに戻ったときの再構築でも合成 id 列を候補に入れない", async () => {
  const { result } = renderHook(() => useInputData(jest.fn()));
  const file = shortAnswerCsv();
  act(() => {
    result.current.setCsv(file);
  });
  act(() => {
    result.current.setInputType("spreadsheet");
  });
  act(() => {
    result.current.setInputType("file");
  });
  await settleParses();

  expect(result.current.csvColumns).toEqual(["回答"]);
  expect(result.current.selectedCommentColumn).toBe("回答");
});

it("CSV タブに戻った直後にファイルを外すと、遅れて終わった解析で列候補を復活させない", async () => {
  const onDataLoaded = jest.fn();
  const { result } = renderHook(() => useInputData(onDataLoaded));
  const file = shortAnswerCsv();
  act(() => {
    result.current.setCsv(file);
  });
  act(() => {
    result.current.setInputType("spreadsheet");
  });

  let finish!: () => void;
  const rows = await actualParseCsv(file);
  jest.mocked(parseCsv).mockReturnValueOnce(
    new Promise((resolve) => {
      finish = () => resolve(rows);
    }),
  );
  act(() => {
    result.current.setInputType("file");
  });
  act(() => {
    result.current.setCsv(null);
  });
  await act(async () => finish());
  await settleParses();

  expect(result.current.csv).toBeNull();
  expect(result.current.csvColumns).toEqual([]);
  expect(onDataLoaded).not.toHaveBeenCalled();
});

it("getBestCommentColumn は id・comment-id 列を選ばない", () => {
  const data = [
    { id: "csv-1", "comment-id": "c-0001", 回答: "はい" },
    { id: "csv-2", "comment-id": "c-0002", 回答: "いいえ" },
  ];
  expect(getBestCommentColumn(data)).toBe("回答");
});
