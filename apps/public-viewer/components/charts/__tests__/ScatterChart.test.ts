import { applyScatterChartDomOverrides, avoidModeBarCoveringShrinkButton } from "../ScatterChart";

describe("ScatterChart DOM helpers", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("modebar container ignores pointer events while the toolbar remains clickable", () => {
    document.body.innerHTML = `
      <div class="modebar-container" style="top: 0px;">
        <div class="modebar"></div>
      </div>
    `;

    applyScatterChartDomOverrides();

    const modeBarContainer = document.querySelector(".modebar-container") as HTMLElement;
    const modeBar = modeBarContainer.children[0] as HTMLElement;

    expect(modeBarContainer.style.pointerEvents).toBe("none");
    expect(modeBar.style.pointerEvents).toBe("auto");
  });

  it("moves the modebar below the fullscreen buttons when they overlap", () => {
    document.body.innerHTML = `
      <div class="modebar-container" style="top: 10px;">
        <div class="modebar"></div>
      </div>
      <div id="fullScreenButtons"></div>
    `;

    const modeBarContainer = document.querySelector(".modebar-container") as HTMLElement;
    const modeBar = modeBarContainer.children[0] as HTMLElement;
    const shrinkButton = document.getElementById("fullScreenButtons") as HTMLElement;

    modeBar.getBoundingClientRect = jest.fn(() => ({
      top: 0,
      right: 120,
      bottom: 20,
      left: 0,
      width: 120,
      height: 20,
      x: 0,
      y: 0,
      toJSON: () => {},
    }));
    shrinkButton.getBoundingClientRect = jest.fn(() => ({
      top: 5,
      right: 100,
      bottom: 25,
      left: 20,
      width: 80,
      height: 20,
      x: 20,
      y: 5,
      toJSON: () => {},
    }));

    avoidModeBarCoveringShrinkButton(modeBarContainer, modeBar);

    expect(modeBarContainer.style.top).toBe("45px");
  });
});
