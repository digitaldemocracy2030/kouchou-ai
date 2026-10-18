/**
 * @jest-environment node
 */
jest.mock("../_op-image", () => ({
  OpImage: jest.fn(async (slug: string) => `image:${slug}`),
  size: { width: 1200, height: 630 },
  contentType: "image/png",
}));

// static ビルドでは opengraph-image.tsx が改名されて型検査の対象外になるため、
// 静的 import ではなく require で読み込む（import だと build:static の型検査が失敗する）
const { default: OgImage } = require("../opengraph-image") as {
  default: (props: { params: Promise<{ slug: string }> }) => Promise<unknown>;
};

describe("opengraph-image", () => {
  it("Promise で渡される params を await して slug を OpImage に渡す", async () => {
    // Next 16 ではメタデータ画像ルートの params は素の Promise になる
    const params = Promise.resolve({ slug: "my-report" });
    await expect(OgImage({ params })).resolves.toBe("image:my-report");
  });
});
