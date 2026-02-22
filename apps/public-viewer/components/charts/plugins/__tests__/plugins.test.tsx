/**
 * Tests for individual chart plugins
 */

import type { Result } from "@/type";
import { hierarchyListPlugin } from "../hierarchy-list";
import { scatterPlugin } from "../scatter";
import { treemapPlugin } from "../treemap";

// Mock chart components
jest.mock("../../ScatterChart", () => ({
  ScatterChart: () => null,
}));

jest.mock("../../TreemapChart", () => ({
  TreemapChart: () => null,
}));

jest.mock("../../HierarchyListChart", () => ({
  HierarchyListChart: () => null,
}));

// Mock icons
jest.mock("@/components/icons/ViewIcons", () => ({
  AllViewIcon: () => null,
  DenseViewIcon: () => null,
  DetailViewIcon: () => null,
  HierarchyViewIcon: () => null,
  ListViewIcon: () => null,
}));

describe("scatterPlugin", () => {
  describe("manifest", () => {
    it("has correct plugin ID", () => {
      expect(scatterPlugin.manifest.id).toBe("scatter");
    });

    it("has three modes: scatterAll, scatterDetail, and scatterDensity", () => {
      const modes = scatterPlugin.manifest.modes;
      expect(modes).toHaveLength(3);
      expect(modes.map((m) => m.id)).toEqual(["scatterAll", "scatterDetail", "scatterDensity"]);
    });

    it("scatterDetail mode can be disabled", () => {
      const detailMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDetail");
      expect(detailMode?.canBeDisabled).toBe(true);
    });

    it("scatterDetail isDisabled returns true when maxLevel <= 1", () => {
      const detailMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDetail");
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
        ],
        arguments: [],
        config: { title: "Test" },
      };
      expect(detailMode?.isDisabled?.(result)).toBe(true);
    });

    it("scatterDetail isDisabled returns false when maxLevel > 1", () => {
      const detailMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDetail");
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test1", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
          { id: "2", level: 2, label: "Test2", takeaways: "", value: 5, density_rank_percentile: 0.3, x: 1, y: 1 },
        ],
        arguments: [],
        config: { title: "Test" },
      };
      expect(detailMode?.isDisabled?.(result)).toBe(false);
    });

    it("scatterDensity mode can be disabled", () => {
      const densityMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDensity");
      expect(densityMode?.canBeDisabled).toBe(true);
    });

    it("scatterDensity isDisabled returns true when maxLevel <= 1", () => {
      const densityMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDensity");
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
        ],
        arguments: [],
        config: { title: "Test" },
      };

      expect(densityMode?.isDisabled?.(result)).toBe(true);
    });

    it("scatterDensity isDisabled returns false when maxLevel > 1", () => {
      const densityMode = scatterPlugin.manifest.modes.find((m) => m.id === "scatterDensity");
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test1", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
          { id: "2", level: 2, label: "Test2", takeaways: "", value: 5, density_rank_percentile: 0.3, x: 1, y: 1 },
        ],
        arguments: [],
        config: { title: "Test" },
      };

      expect(densityMode?.isDisabled?.(result)).toBe(false);
    });
  });

  describe("canHandle", () => {
    it("returns true for scatterAll", () => {
      expect(scatterPlugin.canHandle("scatterAll")).toBe(true);
    });

    it("returns true for scatterDetail", () => {
      expect(scatterPlugin.canHandle("scatterDetail")).toBe(true);
    });

    it("returns true for scatterDensity", () => {
      expect(scatterPlugin.canHandle("scatterDensity")).toBe(true);
    });

    it("returns false for other modes", () => {
      expect(scatterPlugin.canHandle("treemap")).toBe(false);
      expect(scatterPlugin.canHandle("hierarchyList")).toBe(false);
      expect(scatterPlugin.canHandle("unknown")).toBe(false);
    });
  });

  describe("render", () => {
    it("renders without error", () => {
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
        ],
        arguments: [],
        config: { title: "Test" },
      };

      const element = scatterPlugin.render({
        result,
        selectedChart: "scatterAll",
        isFullscreen: false,
        showClusterLabels: true,
      });

      expect(element).not.toBeNull();
    });
  });
});

describe("treemapPlugin", () => {
  describe("manifest", () => {
    it("has correct plugin ID", () => {
      expect(treemapPlugin.manifest.id).toBe("treemap");
    });

    it("has one mode: treemap", () => {
      const modes = treemapPlugin.manifest.modes;
      expect(modes).toHaveLength(1);
      expect(modes[0].id).toBe("treemap");
    });

    it("has proper version", () => {
      expect(treemapPlugin.manifest.version).toBe("1.0.0");
    });
  });

  describe("canHandle", () => {
    it("returns true for treemap", () => {
      expect(treemapPlugin.canHandle("treemap")).toBe(true);
    });

    it("returns false for other modes", () => {
      expect(treemapPlugin.canHandle("scatterAll")).toBe(false);
      expect(treemapPlugin.canHandle("hierarchyList")).toBe(false);
    });
  });

  describe("render", () => {
    it("renders without error", () => {
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
        ],
        arguments: [],
        config: { title: "Test" },
      };

      const element = treemapPlugin.render({
        result,
        selectedChart: "treemap",
        isFullscreen: false,
        treemapLevel: "0",
        onTreeZoom: jest.fn(),
      });

      expect(element).not.toBeNull();
    });
  });
});

describe("hierarchyListPlugin", () => {
  describe("manifest", () => {
    it("has correct plugin ID", () => {
      expect(hierarchyListPlugin.manifest.id).toBe("hierarchy-list");
    });

    it("has one mode: hierarchyList", () => {
      const modes = hierarchyListPlugin.manifest.modes;
      expect(modes).toHaveLength(1);
      expect(modes[0].id).toBe("hierarchyList");
    });

    it("has proper version", () => {
      expect(hierarchyListPlugin.manifest.version).toBe("1.0.0");
    });

    it("has Japanese name", () => {
      expect(hierarchyListPlugin.manifest.name).toBe("階層リスト");
    });
  });

  describe("canHandle", () => {
    it("returns true for hierarchyList", () => {
      expect(hierarchyListPlugin.canHandle("hierarchyList")).toBe(true);
    });

    it("returns false for other modes", () => {
      expect(hierarchyListPlugin.canHandle("scatterAll")).toBe(false);
      expect(hierarchyListPlugin.canHandle("treemap")).toBe(false);
    });
  });

  describe("render", () => {
    it("renders without error", () => {
      const result: Result = {
        clusters: [
          { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
        ],
        arguments: [],
        config: { title: "Test" },
      };

      const element = hierarchyListPlugin.render({
        result,
        selectedChart: "hierarchyList",
        isFullscreen: false,
      });

      expect(element).not.toBeNull();
    });
  });
});

describe("Plugin consistency", () => {
  const allPlugins = [scatterPlugin, treemapPlugin, hierarchyListPlugin];

  it("all plugins have unique IDs", () => {
    const ids = allPlugins.map((p) => p.manifest.id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(ids.length);
  });

  it("all plugins have required manifest fields", () => {
    for (const plugin of allPlugins) {
      expect(plugin.manifest.id).toBeTruthy();
      expect(plugin.manifest.name).toBeTruthy();
      expect(plugin.manifest.description).toBeTruthy();
      expect(plugin.manifest.version).toBeTruthy();
      expect(plugin.manifest.icon).toBeDefined();
      expect(Array.isArray(plugin.manifest.modes)).toBe(true);
    }
  });

  it("all mode IDs across plugins are unique", () => {
    const modeIds: string[] = [];
    for (const plugin of allPlugins) {
      for (const mode of plugin.manifest.modes) {
        modeIds.push(mode.id);
      }
    }
    const uniqueModeIds = new Set(modeIds);
    expect(uniqueModeIds.size).toBe(modeIds.length);
  });

  it("all plugins implement canHandle correctly", () => {
    for (const plugin of allPlugins) {
      // Each plugin should handle its own modes
      for (const mode of plugin.manifest.modes) {
        expect(plugin.canHandle(mode.id)).toBe(true);
      }
    }
  });

  it("all plugins implement render function", () => {
    for (const plugin of allPlugins) {
      expect(typeof plugin.render).toBe("function");
    }
  });
});
