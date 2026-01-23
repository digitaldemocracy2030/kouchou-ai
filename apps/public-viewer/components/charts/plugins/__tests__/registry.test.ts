/**
 * Tests for Chart Plugin Registry
 */

import type { ChartMode, ChartPlugin } from "../types";

// Mock the require calls in registry
jest.mock("../scatter", () => ({
  scatterPlugin: {
    manifest: {
      id: "scatter",
      name: "散布図",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [
        { id: "scatterAll", label: "全体", icon: () => null },
        { id: "scatterDensity", label: "濃い意見", icon: () => null },
      ],
    },
    canHandle: (mode: string) => mode === "scatterAll" || mode === "scatterDensity",
    render: () => null,
  },
}));

jest.mock("../treemap", () => ({
  treemapPlugin: {
    manifest: {
      id: "treemap",
      name: "ツリーマップ",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [{ id: "treemap", label: "階層", icon: () => null }],
    },
    canHandle: (mode: string) => mode === "treemap",
    render: () => null,
  },
}));

jest.mock("../hierarchy-list", () => ({
  hierarchyListPlugin: {
    manifest: {
      id: "hierarchy-list",
      name: "階層リスト",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [{ id: "hierarchyList", label: "リスト", icon: () => null }],
    },
    canHandle: (mode: string) => mode === "hierarchyList",
    render: () => null,
  },
}));

// Import after mocks
import { chartRegistry, ensurePluginsLoaded, loadBuiltinChartPlugins } from "../registry";

describe("ChartPluginRegistry", () => {
  beforeEach(() => {
    // Clear registry before each test
    chartRegistry.clear();
  });

  describe("register", () => {
    it("registers a plugin successfully", () => {
      const mockPlugin: ChartPlugin = {
        manifest: {
          id: "test-plugin",
          name: "Test Plugin",
          description: "A test plugin",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "testMode", label: "Test", icon: () => null }],
        },
        canHandle: (mode: string) => mode === "testMode",
        render: () => null,
      };

      chartRegistry.register(mockPlugin);

      expect(chartRegistry.get("test-plugin")).toBe(mockPlugin);
    });

    it("maps modes to plugin for lookup", () => {
      const mockPlugin: ChartPlugin = {
        manifest: {
          id: "test-plugin",
          name: "Test Plugin",
          description: "A test plugin",
          version: "1.0.0",
          icon: () => null,
          modes: [
            { id: "mode1", label: "Mode 1", icon: () => null },
            { id: "mode2", label: "Mode 2", icon: () => null },
          ],
        },
        canHandle: (mode: string) => mode === "mode1" || mode === "mode2",
        render: () => null,
      };

      chartRegistry.register(mockPlugin);

      expect(chartRegistry.getByMode("mode1")).toBe(mockPlugin);
      expect(chartRegistry.getByMode("mode2")).toBe(mockPlugin);
    });

    it("warns on plugin ID collision but still registers", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

      const plugin1: ChartPlugin = {
        manifest: {
          id: "duplicate-plugin",
          name: "Plugin 1",
          description: "First plugin",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "mode1", label: "Mode 1", icon: () => null }],
        },
        canHandle: () => true,
        render: () => null,
      };

      const plugin2: ChartPlugin = {
        manifest: {
          id: "duplicate-plugin",
          name: "Plugin 2",
          description: "Second plugin",
          version: "2.0.0",
          icon: () => null,
          modes: [{ id: "mode2", label: "Mode 2", icon: () => null }],
        },
        canHandle: () => true,
        render: () => null,
      };

      chartRegistry.register(plugin1);
      chartRegistry.register(plugin2);

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Chart plugin collision: "duplicate-plugin"'));
      expect(chartRegistry.get("duplicate-plugin")).toBe(plugin2);

      consoleSpy.mockRestore();
    });

    it("warns on mode ID collision", () => {
      const consoleSpy = jest.spyOn(console, "warn").mockImplementation();

      const plugin1: ChartPlugin = {
        manifest: {
          id: "plugin1",
          name: "Plugin 1",
          description: "First plugin",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "sharedMode", label: "Shared", icon: () => null }],
        },
        canHandle: () => true,
        render: () => null,
      };

      const plugin2: ChartPlugin = {
        manifest: {
          id: "plugin2",
          name: "Plugin 2",
          description: "Second plugin",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "sharedMode", label: "Shared Again", icon: () => null }],
        },
        canHandle: () => true,
        render: () => null,
      };

      chartRegistry.register(plugin1);
      chartRegistry.register(plugin2);

      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Chart mode collision: "sharedMode"'));
      expect(chartRegistry.getByMode("sharedMode")).toBe(plugin2);

      consoleSpy.mockRestore();
    });
  });

  describe("get", () => {
    it("returns undefined for unregistered plugin", () => {
      expect(chartRegistry.get("nonexistent")).toBeUndefined();
    });

    it("returns the registered plugin", () => {
      const mockPlugin: ChartPlugin = {
        manifest: {
          id: "my-plugin",
          name: "My Plugin",
          description: "test",
          version: "1.0.0",
          icon: () => null,
          modes: [],
        },
        canHandle: () => false,
        render: () => null,
      };

      chartRegistry.register(mockPlugin);
      expect(chartRegistry.get("my-plugin")).toBe(mockPlugin);
    });
  });

  describe("getByMode", () => {
    it("returns undefined for unregistered mode", () => {
      expect(chartRegistry.getByMode("nonexistent")).toBeUndefined();
    });
  });

  describe("getAll", () => {
    it("returns empty array when no plugins registered", () => {
      expect(chartRegistry.getAll()).toEqual([]);
    });

    it("returns all registered plugins", () => {
      const plugin1: ChartPlugin = {
        manifest: { id: "p1", name: "P1", description: "", version: "1.0.0", icon: () => null, modes: [] },
        canHandle: () => false,
        render: () => null,
      };
      const plugin2: ChartPlugin = {
        manifest: { id: "p2", name: "P2", description: "", version: "1.0.0", icon: () => null, modes: [] },
        canHandle: () => false,
        render: () => null,
      };

      chartRegistry.register(plugin1);
      chartRegistry.register(plugin2);

      const all = chartRegistry.getAll();
      expect(all).toHaveLength(2);
      expect(all).toContain(plugin1);
      expect(all).toContain(plugin2);
    });
  });

  describe("getAllModes", () => {
    it("returns empty array when no plugins registered", () => {
      expect(chartRegistry.getAllModes()).toEqual([]);
    });

    it("returns all modes from all plugins", () => {
      const mode1: ChartMode = { id: "m1", label: "M1", icon: () => null };
      const mode2: ChartMode = { id: "m2", label: "M2", icon: () => null };
      const mode3: ChartMode = { id: "m3", label: "M3", icon: () => null };

      const plugin1: ChartPlugin = {
        manifest: { id: "p1", name: "P1", description: "", version: "1.0.0", icon: () => null, modes: [mode1, mode2] },
        canHandle: () => false,
        render: () => null,
      };
      const plugin2: ChartPlugin = {
        manifest: { id: "p2", name: "P2", description: "", version: "1.0.0", icon: () => null, modes: [mode3] },
        canHandle: () => false,
        render: () => null,
      };

      chartRegistry.register(plugin1);
      chartRegistry.register(plugin2);

      const allModes = chartRegistry.getAllModes();
      expect(allModes).toHaveLength(3);
      expect(allModes).toContain(mode1);
      expect(allModes).toContain(mode2);
      expect(allModes).toContain(mode3);
    });
  });

  describe("hasMode", () => {
    it("returns false for unregistered mode", () => {
      expect(chartRegistry.hasMode("nonexistent")).toBe(false);
    });

    it("returns true for registered mode", () => {
      const plugin: ChartPlugin = {
        manifest: {
          id: "p1",
          name: "P1",
          description: "",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "myMode", label: "My Mode", icon: () => null }],
        },
        canHandle: () => false,
        render: () => null,
      };

      chartRegistry.register(plugin);
      expect(chartRegistry.hasMode("myMode")).toBe(true);
    });
  });

  describe("clear", () => {
    it("removes all plugins and modes", () => {
      const plugin: ChartPlugin = {
        manifest: {
          id: "p1",
          name: "P1",
          description: "",
          version: "1.0.0",
          icon: () => null,
          modes: [{ id: "m1", label: "M1", icon: () => null }],
        },
        canHandle: () => false,
        render: () => null,
      };

      chartRegistry.register(plugin);
      expect(chartRegistry.getAll()).toHaveLength(1);
      expect(chartRegistry.hasMode("m1")).toBe(true);

      chartRegistry.clear();

      expect(chartRegistry.getAll()).toHaveLength(0);
      expect(chartRegistry.hasMode("m1")).toBe(false);
    });
  });
});

describe("loadBuiltinChartPlugins", () => {
  beforeEach(() => {
    chartRegistry.clear();
  });

  it("loads all built-in plugins", () => {
    const consoleSpy = jest.spyOn(console, "debug").mockImplementation();

    loadBuiltinChartPlugins();

    // Should have scatter, treemap, and hierarchy-list plugins
    expect(chartRegistry.get("scatter")).toBeDefined();
    expect(chartRegistry.get("treemap")).toBeDefined();
    expect(chartRegistry.get("hierarchy-list")).toBeDefined();

    consoleSpy.mockRestore();
  });

  it("registers all expected modes", () => {
    const consoleSpy = jest.spyOn(console, "debug").mockImplementation();

    loadBuiltinChartPlugins();

    // Check all modes are registered
    expect(chartRegistry.hasMode("scatterAll")).toBe(true);
    expect(chartRegistry.hasMode("scatterDensity")).toBe(true);
    expect(chartRegistry.hasMode("treemap")).toBe(true);
    expect(chartRegistry.hasMode("hierarchyList")).toBe(true);

    consoleSpy.mockRestore();
  });
});

describe("ensurePluginsLoaded", () => {
  beforeEach(() => {
    chartRegistry.clear();
    // Reset module state for ensurePluginsLoaded
    jest.resetModules();
  });

  it("loads plugins only once", () => {
    const consoleSpy = jest.spyOn(console, "debug").mockImplementation();

    // Re-import to reset initialized state
    const { ensurePluginsLoaded: freshEnsure, chartRegistry: freshRegistry } = require("../registry");
    freshRegistry.clear();

    freshEnsure();
    const firstCount = freshRegistry.getAll().length;

    // Call again - should not add more plugins
    freshEnsure();
    const secondCount = freshRegistry.getAll().length;

    expect(firstCount).toBe(secondCount);

    consoleSpy.mockRestore();
  });
});
