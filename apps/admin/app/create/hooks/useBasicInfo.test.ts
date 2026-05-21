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
