import { darkenPathbar } from "../TreemapChart";

jest.mock("../ChartCore", () => ({ ChartCore: () => null }));

// plotly が描く treemap の DOM（パネルとパスバー）の最小形
function renderTreemapDom(panelFills: string[], pathbarFill: string) {
  document.body.innerHTML = `
    <div class="treemap">
      ${panelFills.map((fill) => `<div class="slice"><div class="surface" style="fill: ${fill}; stroke: white;"></div></div>`).join("")}
      <div class="pathbar"><div class="surface" style="fill: ${pathbarFill};"></div></div>
    </div>`;
  const panels = document.querySelectorAll<HTMLElement>(".treemap > .slice > .surface");
  const pathbar = document.querySelector<HTMLElement>(".treemap > .pathbar > .surface");
  if (!pathbar) throw new Error("pathbar not rendered");
  return { panels, pathbar };
}

describe("darkenPathbar", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("Element.computedStyleMap の無いブラウザ（Firefox・jsdom）でも例外を投げずにパスバーを暗くする", () => {
    expect((Element.prototype as { computedStyleMap?: unknown }).computedStyleMap).toBeUndefined();
    const { panels, pathbar } = renderTreemapDom(["rgb(100, 150, 200)", "rgb(100, 150, 200)"], "rgb(100, 150, 200)");

    expect(() => darkenPathbar()).not.toThrow();

    expect(pathbar.style.fill).toBe("rgb(70, 120, 170)");
    expect(panels[0].style.fill).toBe("rgb(70, 120, 170)");
    // 他の style は残す
    expect(panels[0].style.stroke).toBe("white");
    // 葉のパネルは元の色のまま
    expect(panels[1].style.fill).toBe("rgb(100, 150, 200)");
  });

  it("色が違うパスバーは書き換えない", () => {
    const { pathbar } = renderTreemapDom(["rgb(1, 2, 3)", "rgb(100, 150, 200)"], "rgb(10, 20, 30)");

    darkenPathbar();

    expect(pathbar.style.fill).toBe("rgb(10, 20, 30)");
  });

  it("色の取得に失敗しても例外を外へ投げない（plotly の unhover の後片付けを止めない）", () => {
    renderTreemapDom(["rgb(1, 2, 3)"], "rgb(1, 2, 3)");
    const spy = jest.spyOn(window, "getComputedStyle").mockImplementation(() => {
      throw new Error("boom");
    });
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {});

    expect(() => darkenPathbar()).not.toThrow();

    spy.mockRestore();
    warn.mockRestore();
  });
});
