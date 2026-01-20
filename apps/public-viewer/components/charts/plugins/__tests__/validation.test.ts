/**
 * Tests for Plugin Validation System
 */

import type { ReportDisplayConfig, Result } from "@/type";
import { ChartPluginRegistry } from "../registry";
import type { ChartMode, ChartPlugin, ChartPluginManifest } from "../types";
import {
  assertValidation,
  formatValidationResult,
  validateChartMode,
  validatePlugin,
  validatePluginManifest,
  validateResultData,
  validateVisualizationConfig,
} from "../validation";

// Mock registry for testing - uses register() which triggers validation
function createMockRegistry(): ChartPluginRegistry {
  const registry = new ChartPluginRegistry();

  // Suppress console output during test setup
  const originalWarn = console.warn;
  const originalDebug = console.debug;
  console.warn = () => {};
  console.debug = () => {};

  // Add mock plugin with modes
  const mockPlugin: ChartPlugin = {
    manifest: {
      id: "mock",
      name: "Mock",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [
        { id: "scatterAll", label: "All", icon: () => null },
        { id: "treemap", label: "Tree", icon: () => null },
        { id: "hierarchyList", label: "List", icon: () => null },
      ],
    },
    canHandle: () => true,
    render: () => null,
  };

  // Register plugin (this validates, but we suppress output)
  registry.register(mockPlugin);

  // Restore console
  console.warn = originalWarn;
  console.debug = originalDebug;

  return registry;
}

describe("validatePluginManifest", () => {
  it("passes for valid manifest", () => {
    const manifest: ChartPluginManifest = {
      id: "test-plugin",
      name: "Test Plugin",
      description: "A test plugin",
      version: "1.0.0",
      icon: () => null,
      modes: [{ id: "testMode", label: "Test", icon: () => null }],
    };

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it("fails for missing id", () => {
    const manifest = {
      name: "Test",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [],
    } as unknown as ChartPluginManifest;

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "MANIFEST_MISSING_ID")).toBe(true);
  });

  it("fails for missing name", () => {
    const manifest = {
      id: "test",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [],
    } as unknown as ChartPluginManifest;

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "MANIFEST_MISSING_NAME")).toBe(true);
  });

  it("warns for non-semver version", () => {
    const manifest: ChartPluginManifest = {
      id: "test",
      name: "Test",
      description: "test",
      version: "v1", // Not semver
      icon: () => null,
      modes: [{ id: "m1", label: "M1", icon: () => null }],
    };

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(true);
    expect(result.warnings.some((e) => e.code === "MANIFEST_INVALID_VERSION_FORMAT")).toBe(true);
  });

  it("fails for missing icon", () => {
    const manifest = {
      id: "test",
      name: "Test",
      description: "test",
      version: "1.0.0",
      modes: [],
    } as unknown as ChartPluginManifest;

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "MANIFEST_MISSING_ICON")).toBe(true);
  });

  it("warns for empty modes array", () => {
    const manifest: ChartPluginManifest = {
      id: "test",
      name: "Test",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [],
    };

    const result = validatePluginManifest(manifest);
    expect(result.warnings.some((e) => e.code === "MANIFEST_NO_MODES")).toBe(true);
  });

  it("fails for duplicate mode IDs within plugin", () => {
    const manifest: ChartPluginManifest = {
      id: "test",
      name: "Test",
      description: "test",
      version: "1.0.0",
      icon: () => null,
      modes: [
        { id: "duplicate", label: "Mode 1", icon: () => null },
        { id: "duplicate", label: "Mode 2", icon: () => null },
      ],
    };

    const result = validatePluginManifest(manifest);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "MANIFEST_DUPLICATE_MODE_IDS")).toBe(true);
  });
});

describe("validateChartMode", () => {
  it("passes for valid mode", () => {
    const mode: ChartMode = {
      id: "testMode",
      label: "Test Mode",
      icon: () => null,
    };

    const result = validateChartMode(mode, "test-plugin");
    expect(result.valid).toBe(true);
  });

  it("fails for missing id", () => {
    const mode = {
      label: "Test",
      icon: () => null,
    } as unknown as ChartMode;

    const result = validateChartMode(mode, "test-plugin");
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "MODE_MISSING_ID")).toBe(true);
  });

  it("warns for isDisabled without canBeDisabled", () => {
    const mode: ChartMode = {
      id: "test",
      label: "Test",
      icon: () => null,
      isDisabled: () => false,
      // canBeDisabled not set
    };

    const result = validateChartMode(mode, "test-plugin");
    expect(result.warnings.some((e) => e.code === "MODE_ISDISABLED_WITHOUT_FLAG")).toBe(true);
  });

  it("warns for canBeDisabled without isDisabled", () => {
    const mode: ChartMode = {
      id: "test",
      label: "Test",
      icon: () => null,
      canBeDisabled: true,
      // isDisabled not set
    };

    const result = validateChartMode(mode, "test-plugin");
    expect(result.warnings.some((e) => e.code === "MODE_CANBEDISABLED_WITHOUT_ISDISABLED")).toBe(true);
  });
});

describe("validatePlugin", () => {
  it("passes for valid plugin", () => {
    const plugin: ChartPlugin = {
      manifest: {
        id: "test",
        name: "Test",
        description: "test",
        version: "1.0.0",
        icon: () => null,
        modes: [{ id: "testMode", label: "Test", icon: () => null }],
      },
      canHandle: (mode) => mode === "testMode",
      render: () => null,
    };

    const result = validatePlugin(plugin);
    expect(result.valid).toBe(true);
  });

  it("fails when canHandle returns false for declared mode", () => {
    const plugin: ChartPlugin = {
      manifest: {
        id: "test",
        name: "Test",
        description: "test",
        version: "1.0.0",
        icon: () => null,
        modes: [{ id: "testMode", label: "Test", icon: () => null }],
      },
      canHandle: () => false, // Always returns false
      render: () => null,
    };

    const result = validatePlugin(plugin);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "PLUGIN_CANHANDLE_MISMATCH")).toBe(true);
  });

  it("fails when canHandle throws error", () => {
    const plugin: ChartPlugin = {
      manifest: {
        id: "test",
        name: "Test",
        description: "test",
        version: "1.0.0",
        icon: () => null,
        modes: [{ id: "testMode", label: "Test", icon: () => null }],
      },
      canHandle: () => {
        throw new Error("Test error");
      },
      render: () => null,
    };

    const result = validatePlugin(plugin);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "PLUGIN_CANHANDLE_THROWS")).toBe(true);
  });
});

describe("validateVisualizationConfig", () => {
  it("passes for undefined config", () => {
    const registry = createMockRegistry();
    const result = validateVisualizationConfig(undefined, registry);
    expect(result.valid).toBe(true);
  });

  it("passes for valid config", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: ["scatterAll", "treemap"],
      defaultChart: "scatterAll",
      chartOrder: ["scatterAll", "treemap"],
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.valid).toBe(true);
  });

  it("fails for unknown chart type in enabledCharts", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: ["scatterAll", "unknownChart" as never],
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "CONFIG_UNKNOWN_CHART_TYPE")).toBe(true);
  });

  it("fails for defaultChart not in enabledCharts", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: ["scatterAll"],
      defaultChart: "treemap", // Not in enabledCharts
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.code === "CONFIG_DEFAULT_NOT_IN_ENABLED")).toBe(true);
  });

  it("warns for duplicate enabledCharts", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: ["scatterAll", "scatterAll"],
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.warnings.some((e) => e.code === "CONFIG_DUPLICATE_ENABLED_CHARTS")).toBe(true);
  });

  it("warns for empty enabledCharts", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: [],
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.warnings.some((e) => e.code === "CONFIG_EMPTY_ENABLED_CHARTS")).toBe(true);
  });

  it("warns for missing charts in chartOrder", () => {
    const registry = createMockRegistry();
    const config: ReportDisplayConfig = {
      version: "1.0",
      enabledCharts: ["scatterAll", "treemap"],
      chartOrder: ["scatterAll"], // Missing treemap
    };

    const result = validateVisualizationConfig(config, registry);
    expect(result.warnings.some((e) => e.code === "CONFIG_ENABLED_NOT_IN_ORDER")).toBe(true);
  });
});

describe("validateResultData", () => {
  it("passes for valid result", () => {
    const result: Result = {
      clusters: [
        { id: "1", level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 },
      ],
      arguments: [],
      config: { title: "Test" },
    };

    const validation = validateResultData(result);
    expect(validation.valid).toBe(true);
  });

  it("fails for null result", () => {
    const validation = validateResultData(null as unknown as Result);
    expect(validation.valid).toBe(false);
    expect(validation.errors.some((e) => e.code === "RESULT_NULL")).toBe(true);
  });

  it("warns for empty clusters", () => {
    const result: Result = {
      clusters: [],
      arguments: [],
      config: { title: "Test" },
    };

    const validation = validateResultData(result);
    expect(validation.warnings.some((e) => e.code === "RESULT_NO_CLUSTERS")).toBe(true);
  });

  it("fails for cluster missing id", () => {
    const result: Result = {
      clusters: [
        { level: 1, label: "Test", takeaways: "", value: 10, density_rank_percentile: 0.5, x: 0, y: 0 } as never,
      ],
      arguments: [],
      config: { title: "Test" },
    };

    const validation = validateResultData(result);
    expect(validation.valid).toBe(false);
    expect(validation.errors.some((e) => e.code === "CLUSTER_MISSING_ID")).toBe(true);
  });
});

describe("formatValidationResult", () => {
  it("returns success message for valid result", () => {
    const result = { valid: true, errors: [], warnings: [] };
    expect(formatValidationResult(result)).toBe("✓ Validation passed");
  });

  it("formats errors and warnings", () => {
    const result = {
      valid: false,
      errors: [{ code: "ERR1", message: "Error 1", severity: "error" as const }],
      warnings: [{ code: "WARN1", message: "Warning 1", severity: "warning" as const }],
    };

    const formatted = formatValidationResult(result);
    expect(formatted).toContain("1 error(s)");
    expect(formatted).toContain("[ERR1] Error 1");
    expect(formatted).toContain("1 warning(s)");
    expect(formatted).toContain("[WARN1] Warning 1");
  });
});

describe("assertValidation", () => {
  it("does not throw for valid result", () => {
    const result = { valid: true, errors: [], warnings: [] };
    expect(() => assertValidation(result, "Test")).not.toThrow();
  });

  it("throws for invalid result", () => {
    const result = {
      valid: false,
      errors: [{ code: "ERR1", message: "Error 1", severity: "error" as const }],
      warnings: [],
    };

    expect(() => assertValidation(result, "Test")).toThrow("Test validation failed");
  });
});
