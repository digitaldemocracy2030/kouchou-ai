import { act, renderHook } from "@testing-library/react";
import { getSpreadsheetData, importSpreadsheet } from "../api/spreadsheet";
import { useInputData } from "./useInputData";

jest.mock("../api/spreadsheet", () => ({
  importSpreadsheet: jest.fn(),
  getSpreadsheetData: jest.fn(),
  deleteSpreadsheetData: jest.fn(),
}));

jest.mock("@/components/ui/toaster", () => ({
  toaster: { create: jest.fn() },
}));

const mockImportSpreadsheet = importSpreadsheet as jest.MockedFunction<typeof importSpreadsheet>;
const mockGetSpreadsheetData = getSpreadsheetData as jest.MockedFunction<typeof getSpreadsheetData>;

const comments = Array.from({ length: 3 }, (_, i) => ({ id: `c${i}`, comment: `意見${i}` }));

/** importSpreadsheet を外から解決できるようにして、取り込みの途中でタブを切り替えられるようにする */
function deferImport() {
  let resolve: () => void = () => {};
  mockImportSpreadsheet.mockReturnValue(
    new Promise<void>((r) => {
      resolve = r;
    }),
  );
  mockGetSpreadsheetData.mockResolvedValue({ comments } as unknown as Awaited<ReturnType<typeof getSpreadsheetData>>);
  return () => resolve();
}

describe("useInputData のスプレッドシート取り込み", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("取り込みが終わった時にスプレッドシートのタブにいれば、列とクラスタ数を更新する", async () => {
    const onDataLoaded = jest.fn();
    const { result } = renderHook(() => useInputData(onDataLoaded));
    act(() => {
      result.current.setInputType("spreadsheet");
      result.current.setSpreadsheetUrl("https://docs.google.com/spreadsheets/d/x");
    });
    const finish = deferImport();

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.importSpreadsheet("sheet-id");
    });
    await act(async () => {
      finish();
      await pending;
    });

    expect(onDataLoaded).toHaveBeenCalledWith(comments.length);
    expect(result.current.csvColumns).toEqual(["id", "comment"]);
  });

  it("取り込み中に Polis へ切り替えていたら、列とクラスタ数を上書きせず、戻った時に作り直す", async () => {
    const onDataLoaded = jest.fn();
    const { result } = renderHook(() => useInputData(onDataLoaded));
    act(() => {
      result.current.setInputType("spreadsheet");
      result.current.setSpreadsheetUrl("https://docs.google.com/spreadsheets/d/x");
    });
    const finish = deferImport();

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.importSpreadsheet("sheet-id");
    });
    act(() => {
      result.current.setInputType("polis");
    });
    await act(async () => {
      finish();
      await pending;
    });

    expect(onDataLoaded).not.toHaveBeenCalled();
    expect(result.current.csvColumns).toEqual([]);
    expect(result.current.spreadsheetImported).toBe(true);

    act(() => {
      result.current.setInputType("spreadsheet");
    });
    expect(onDataLoaded).toHaveBeenCalledWith(comments.length);
    expect(result.current.csvColumns).toEqual(["id", "comment"]);
  });
});
