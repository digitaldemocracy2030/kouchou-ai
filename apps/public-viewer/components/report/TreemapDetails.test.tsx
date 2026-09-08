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
