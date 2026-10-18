/**
 * @jest-environment node
 */
import { revalidateTag } from "next/cache";
import { NextRequest } from "next/server";
import { POST } from "../route";

jest.mock("next/cache", () => ({ revalidateTag: jest.fn() }));

describe("POST /api/revalidate", () => {
  const originalSecret = process.env.REVALIDATE_SECRET;

  beforeEach(() => {
    process.env.REVALIDATE_SECRET = "test-secret";
    (revalidateTag as jest.Mock).mockClear();
  });

  afterAll(() => {
    process.env.REVALIDATE_SECRET = originalSecret;
  });

  it("stale-while-revalidate ではなく即時に失効させる（非公開化・削除の直後に古いレポートを返さない）", async () => {
    const request = new NextRequest("http://localhost/api/revalidate", {
      method: "POST",
      body: JSON.stringify({ tag: "report-test-slug", secret: "test-secret" }),
    });
    const response = await POST(request);
    expect(response.status).toBe(200);
    expect(revalidateTag).toHaveBeenCalledWith("report-test-slug", { expire: 0 });
    const body = await response.json();
    expect(body.method).not.toBe("force");
  });
});
