import { createUUID } from "@/app/utils/uuid";
import { act, renderHook } from "@testing-library/react";
import { useBasicInfo } from "./useBasicInfo";

jest.mock("@/app/utils/uuid", () => ({
  createUUID: jest.fn(),
}));

const mockCreateUUID = createUUID as jest.MockedFunction<typeof createUUID>;

describe("useBasicInfo", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("initializes the report id with createUUID", () => {
    mockCreateUUID.mockReturnValue("generated-id");

    const { result } = renderHook(() => useBasicInfo());

    expect(result.current.input).toBe("generated-id");
    expect(mockCreateUUID).toHaveBeenCalledTimes(1);
  });

  it("resets the report id with createUUID", () => {
    mockCreateUUID.mockReturnValueOnce("initial-id").mockReturnValueOnce("reset-id");

    const { result } = renderHook(() => useBasicInfo());

    act(() => {
      result.current.resetBasicInfo();
    });

    expect(result.current.input).toBe("reset-id");
    expect(mockCreateUUID).toHaveBeenCalledTimes(2);
  });
});

describe("CSV filename defaults", () => {
  it.each([
    ["", "", "調査.v2", "調査.v2"],
    ["入力済み", "", "入力済み", "調査.v2"],
    ["", "入力済み", "調査.v2", "入力済み"],
    ["  タイトル  ", "概要", "  タイトル  ", "概要"],
    ["  ", "", "調査.v2", "調査.v2"],
  ])("preserves independently entered fields (%s / %s)", (title, intro, expectedTitle, expectedIntro) => {
    const { result } = renderHook(() => useBasicInfo());
    act(() => {
      result.current.handleQuestionChange({ target: { value: title } } as React.ChangeEvent<HTMLInputElement>);
      result.current.handleIntroChange({ target: { value: intro } } as React.ChangeEvent<HTMLInputElement>);
      result.current.fillEmptyFromCsv(new File(["comment"], "調査.v2.CSV"));
    });
    expect(result.current.question).toBe(expectedTitle);
    expect(result.current.intro).toBe(expectedIntro);
    const id = result.current.input;
    act(() => result.current.fillEmptyFromCsv(null));
    act(() => result.current.fillEmptyFromCsv(new File(["comment"], "別ファイル.csv")));
    expect(result.current.question).toBe(expectedTitle);
    expect(result.current.intro).toBe(expectedIntro);
    expect(result.current.input).toBe(id);
  });
});
