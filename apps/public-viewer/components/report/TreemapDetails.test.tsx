import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { TreemapDetails } from "./TreemapDetails";

it("説明から階層へ移動し、戻ると一覧も復元する", () => {
  const clusters = [
    { id: "0", parent: "", label: "全体", takeaway: "", value: 2 },
    { id: "a", parent: "0", label: "交通", takeaway: "交通の説明", value: 2 },
    { id: "a1", parent: "a", label: "バス", takeaway: "バスの説明", value: 2 },
  ];
  function Viewer() {
    const [level, setLevel] = useState("0");
    return <TreemapDetails clusters={clusters} arguments={[]} level={level} onNavigate={setLevel} />;
  }
  render(<Viewer />);
  fireEvent.click(screen.getByRole("button", { name: "交通" }));
  expect(screen.getByRole("heading", { name: "表示中: 交通" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "バス" }));
  expect(screen.getByRole("heading", { name: "表示中: バス" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "一つ上に戻る" }));
  expect(screen.getByRole("button", { name: "バス" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "一つ上に戻る" }));
  expect(screen.getByRole("button", { name: "交通" })).toBeInTheDocument();
});

const root = { id: "0", parent: "", label: "全体", takeaway: "", value: 2 };
const leaf = { id: "a", parent: "0", label: "交通", takeaway: "", value: 2 };
const sharedReport = {
  clusters: [root, leaf],
  arguments: [
    { arg_id: "A1", argument: "電車", cluster_ids: ["0", "a"], comment_id: "shared" },
    { arg_id: "A2", argument: "バス", cluster_ids: ["0", "a"], comment_id: "shared", comment_ids: ["shared", "extra"] },
  ],
  comments: { shared: { comment: "長い共通の原文" }, extra: { comment: "バスの別の原文" } },
  showOriginalComments: true,
  onNavigate: () => {},
};

it("末端のグループの元コメントを重複なく出し、個別意見ではその出典だけを出す", async () => {
  const { rerender } = render(
    <Provider>
      <TreemapDetails {...sharedReport} level="0" />
    </Provider>,
  );
  expect(screen.queryByRole("region", { name: /元コメント/ })).not.toBeInTheDocument();
  rerender(
    <Provider>
      <TreemapDetails {...sharedReport} level="a" />
    </Provider>,
  );
  expect(screen.getByRole("region", { name: "元コメント 2件" })).toBeInTheDocument();
  fireEvent.click(screen.getByText("元コメント 1", { exact: true }));
  expect(await screen.findAllByText("長い共通の原文")).toHaveLength(1);

  rerender(
    <Provider>
      <TreemapDetails {...sharedReport} level="A1" />
    </Provider>,
  );
  expect(screen.getByRole("region", { name: "元コメント 1件" })).toBeInTheDocument();
  expect(screen.queryByText("長い共通の原文")).not.toBeInTheDocument();
  expect(screen.queryByText("元コメント 2", { exact: true })).not.toBeInTheDocument();
});

it("属性フィルター適用時に、除外された意見だけが参照する本文を出さない", async () => {
  render(
    <Provider>
      <TreemapDetails {...sharedReport} level="a" filteredIds={["A1"]} />
    </Provider>,
  );
  expect(screen.getByRole("region", { name: "元コメント 1件" })).toBeInTheDocument();
  fireEvent.click(screen.getByText("元コメント 1", { exact: true }));
  expect(await screen.findByText("長い共通の原文")).toBeVisible();
  expect(screen.queryByText("元コメント 2", { exact: true })).not.toBeInTheDocument();
});
