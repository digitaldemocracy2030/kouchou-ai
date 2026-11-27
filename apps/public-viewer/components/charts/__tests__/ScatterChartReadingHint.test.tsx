import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { render, screen } from "@testing-library/react";
import { ScatterHint } from "../ScatterChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

jest.mock("../ChartCore", () => ({ ChartCore: () => null }));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

function renderHint(
  props: Partial<{
    showConvexHull: boolean;
    showOriginalComments: boolean;
    showSourceLink: boolean;
    showSelectGroup: boolean;
  }>,
) {
  render(
    <Provider>
      <ScatterHint showConvexHull={false} showOriginalComments={false} showSourceLink={false} {...props} />
    </Provider>,
  );
}

describe("散布図のヒントの見方（#1212）", () => {
  it("点・軸・件数の見方を、操作方法より先に出す", () => {
    renderHint({});
    const reading = screen.getByText("散布図の見方");
    const operation = screen.getByText("散布図の操作方法");
    expect(reading.compareDocumentPosition(operation) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/点 1 つが、抽出した意見 1 件です/)).toBeInTheDocument();
    expect(screen.getByText(/縦軸・横軸そのものに意味はありません/)).toBeInTheDocument();
    expect(screen.getByText(/重要度や賛成の多さを表すものではありません/)).toBeInTheDocument();
  });

  it("輪郭の重なりの読み方は、輪郭を描いているときだけ出す", () => {
    renderHint({ showConvexHull: true });
    expect(screen.getByText(/輪郭が重なって見えても/)).toBeInTheDocument();
  });

  it("輪郭を描いていないときは、輪郭の説明を出さない", () => {
    renderHint({ showConvexHull: false });
    expect(screen.queryByText(/輪郭が重なって見えても/)).not.toBeInTheDocument();
  });

  it("ソースリンク・元コメントの操作は、それぞれ有効なときだけ案内する", () => {
    renderHint({ showSourceLink: true });
    expect(screen.getByText(/元のソースを開く/)).toBeInTheDocument();
    expect(screen.queryByText(/元コメントの本文も表示/)).not.toBeInTheDocument();
  });

  it("点のクリックでグループの説明を出す操作は、グループを選べるときだけ案内する（#1207）", () => {
    renderHint({ showSelectGroup: true });
    expect(screen.getByText(/図の下に、そのグループの説明を表示/)).toBeInTheDocument();
  });

  it("グループの選択とソースリンクが両方有効なときは、点のクリックの説明を 1 行にまとめる", () => {
    renderHint({ showSelectGroup: true, showSourceLink: true });
    expect(screen.getAllByText(/点をクリック/)).toHaveLength(1);
    expect(screen.getByText(/そのグループの説明を表示し、元のソースを開く/)).toBeInTheDocument();
  });

  it("グループを選べないとき（全画面など）は、グループの説明の操作を案内しない", () => {
    renderHint({ showSelectGroup: false });
    expect(screen.queryByText(/そのグループの説明を表示/)).not.toBeInTheDocument();
  });
});
