/**
 * Plugin Validation System
 *
 * Provides compile-time-like validation for plugin configurations
 * to catch errors early and provide clear debugging messages.
 */

import type { ReportDisplayConfig, Result } from "@/type";
import type { ChartPluginRegistry } from "./registry";
import type { ChartMode, ChartPlugin, ChartPluginManifest } from "./types";

/**
 * Validation error with context for debugging
 */
export interface ValidationError {
  code: string;
  message: string;
  severity: "error" | "warning";
  context?: Record<string, unknown>;
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

/**
 * Create an empty validation result
 */
function createResult(): ValidationResult {
  return { valid: true, errors: [], warnings: [] };
}

/**
 * Add an error to the result
 */
function addError(result: ValidationResult, error: ValidationError): void {
  if (error.severity === "error") {
    result.valid = false;
    result.errors.push(error);
  } else {
    result.warnings.push(error);
  }
}

// ============================================================================
// Plugin Manifest Validation
// ============================================================================

/**
 * Validate a plugin manifest before registration
 */
export function validatePluginManifest(manifest: ChartPluginManifest): ValidationResult {
  const result = createResult();

  // Required fields
  if (!manifest.id || typeof manifest.id !== "string") {
    addError(result, {
      code: "MANIFEST_MISSING_ID",
      message: "Plugin manifest must have a non-empty string 'id'",
      severity: "error",
      context: { manifest },
    });
  }

  if (!manifest.name || typeof manifest.name !== "string") {
    addError(result, {
      code: "MANIFEST_MISSING_NAME",
      message: `Plugin '${manifest.id}' must have a non-empty string 'name'`,
      severity: "error",
      context: { pluginId: manifest.id },
    });
  }

  if (!manifest.version || typeof manifest.version !== "string") {
    addError(result, {
      code: "MANIFEST_MISSING_VERSION",
      message: `Plugin '${manifest.id}' must have a non-empty string 'version'`,
      severity: "error",
      context: { pluginId: manifest.id },
    });
  }

  // Semver format check (warning only)
  if (manifest.version && !/^\d+\.\d+\.\d+/.test(manifest.version)) {
    addError(result, {
      code: "MANIFEST_INVALID_VERSION_FORMAT",
      message: `Plugin '${manifest.id}' version '${manifest.version}' does not follow semver format (x.y.z)`,
      severity: "warning",
      context: { pluginId: manifest.id, version: manifest.version },
    });
  }

  if (!manifest.icon) {
    addError(result, {
      code: "MANIFEST_MISSING_ICON",
      message: `Plugin '${manifest.id}' must have an 'icon' component`,
      severity: "error",
      context: { pluginId: manifest.id },
    });
  }

  // Modes validation
  if (!Array.isArray(manifest.modes)) {
    addError(result, {
      code: "MANIFEST_MODES_NOT_ARRAY",
      message: `Plugin '${manifest.id}' modes must be an array`,
      severity: "error",
      context: { pluginId: manifest.id },
    });
  } else if (manifest.modes.length === 0) {
    addError(result, {
      code: "MANIFEST_NO_MODES",
      message: `Plugin '${manifest.id}' must define at least one mode`,
      severity: "warning",
      context: { pluginId: manifest.id },
    });
  } else {
    // Validate each mode
    for (const mode of manifest.modes) {
      const modeResult = validateChartMode(mode, manifest.id);
      result.errors.push(...modeResult.errors);
      result.warnings.push(...modeResult.warnings);
      if (!modeResult.valid) {
        result.valid = false;
      }
    }

    // Check for duplicate mode IDs within the plugin
    const modeIds = manifest.modes.map((m) => m.id);
    const duplicates = modeIds.filter((id, index) => modeIds.indexOf(id) !== index);
    if (duplicates.length > 0) {
      addError(result, {
        code: "MANIFEST_DUPLICATE_MODE_IDS",
        message: `Plugin '${manifest.id}' has duplicate mode IDs: ${duplicates.join(", ")}`,
        severity: "error",
        context: { pluginId: manifest.id, duplicates },
      });
    }
  }

  return result;
}

/**
 * Validate a chart mode
 */
export function validateChartMode(mode: ChartMode, pluginId: string): ValidationResult {
  const result = createResult();

  if (!mode.id || typeof mode.id !== "string") {
    addError(result, {
      code: "MODE_MISSING_ID",
      message: `Mode in plugin '${pluginId}' must have a non-empty string 'id'`,
      severity: "error",
      context: { pluginId, mode },
    });
  }

  if (!mode.label || typeof mode.label !== "string") {
    addError(result, {
      code: "MODE_MISSING_LABEL",
      message: `Mode '${mode.id}' in plugin '${pluginId}' must have a non-empty string 'label'`,
      severity: "error",
      context: { pluginId, modeId: mode.id },
    });
  }

  if (!mode.icon) {
    addError(result, {
      code: "MODE_MISSING_ICON",
      message: `Mode '${mode.id}' in plugin '${pluginId}' must have an 'icon' component`,
      severity: "error",
      context: { pluginId, modeId: mode.id },
    });
  }

  // isDisabled without canBeDisabled is suspicious
  if (mode.isDisabled && !mode.canBeDisabled) {
    addError(result, {
      code: "MODE_ISDISABLED_WITHOUT_FLAG",
      message: `Mode '${mode.id}' has isDisabled function but canBeDisabled is not set to true`,
      severity: "warning",
      context: { pluginId, modeId: mode.id },
    });
  }

  // canBeDisabled without isDisabled or disabledTooltip
  if (mode.canBeDisabled && !mode.isDisabled) {
    addError(result, {
      code: "MODE_CANBEDISABLED_WITHOUT_ISDISABLED",
      message: `Mode '${mode.id}' has canBeDisabled=true but no isDisabled function`,
      severity: "warning",
      context: { pluginId, modeId: mode.id },
    });
  }

  return result;
}

/**
 * Validate a complete plugin
 */
export function validatePlugin(plugin: ChartPlugin): ValidationResult {
  const result = validatePluginManifest(plugin.manifest);

  // Validate canHandle function
  if (typeof plugin.canHandle !== "function") {
    addError(result, {
      code: "PLUGIN_CANHANDLE_NOT_FUNCTION",
      message: `Plugin '${plugin.manifest.id}' canHandle must be a function`,
      severity: "error",
      context: { pluginId: plugin.manifest.id },
    });
  } else {
    // Verify canHandle returns true for declared modes
    for (const mode of plugin.manifest.modes) {
      try {
        const canHandle = plugin.canHandle(mode.id);
        if (!canHandle) {
          addError(result, {
            code: "PLUGIN_CANHANDLE_MISMATCH",
            message: `Plugin '${plugin.manifest.id}' canHandle('${mode.id}') returns false but mode is declared in manifest`,
            severity: "error",
            context: { pluginId: plugin.manifest.id, modeId: mode.id },
          });
        }
      } catch (e) {
        addError(result, {
          code: "PLUGIN_CANHANDLE_THROWS",
          message: `Plugin '${plugin.manifest.id}' canHandle('${mode.id}') threw an error: ${e}`,
          severity: "error",
          context: { pluginId: plugin.manifest.id, modeId: mode.id, error: String(e) },
        });
      }
    }
  }

  // Validate render function
  if (typeof plugin.render !== "function") {
    addError(result, {
      code: "PLUGIN_RENDER_NOT_FUNCTION",
      message: `Plugin '${plugin.manifest.id}' render must be a function`,
      severity: "error",
      context: { pluginId: plugin.manifest.id },
    });
  }

  return result;
}

// ============================================================================
// Visualization Config Validation
// ============================================================================

/**
 * Validate visualization config against registered plugins
 */
export function validateVisualizationConfig(
  config: ReportDisplayConfig | undefined,
  registry: ChartPluginRegistry,
): ValidationResult {
  const result = createResult();

  if (!config) {
    // No config is valid (uses defaults)
    return result;
  }

  const registeredModes = new Set(registry.getAllModes().map((m) => m.id));

  // Validate enabledCharts
  if (config.enabledCharts) {
    if (!Array.isArray(config.enabledCharts)) {
      addError(result, {
        code: "CONFIG_ENABLED_CHARTS_NOT_ARRAY",
        message: "visualizationConfig.enabledCharts must be an array",
        severity: "error",
        context: { enabledCharts: config.enabledCharts },
      });
    } else {
      for (const chartId of config.enabledCharts) {
        if (!registeredModes.has(chartId)) {
          addError(result, {
            code: "CONFIG_UNKNOWN_CHART_TYPE",
            message: `visualizationConfig.enabledCharts contains unknown chart type '${chartId}'. Available: ${Array.from(registeredModes).join(", ")}`,
            severity: "error",
            context: { chartId, availableModes: Array.from(registeredModes) },
          });
        }
      }

      // Check for duplicates
      const duplicates = config.enabledCharts.filter((id, index) => config.enabledCharts.indexOf(id) !== index);
      if (duplicates.length > 0) {
        addError(result, {
          code: "CONFIG_DUPLICATE_ENABLED_CHARTS",
          message: `visualizationConfig.enabledCharts contains duplicates: ${duplicates.join(", ")}`,
          severity: "warning",
          context: { duplicates },
        });
      }

      if (config.enabledCharts.length === 0) {
        addError(result, {
          code: "CONFIG_EMPTY_ENABLED_CHARTS",
          message: "visualizationConfig.enabledCharts is empty - no charts will be displayed",
          severity: "warning",
          context: {},
        });
      }
    }
  }

  // Validate defaultChart
  if (config.defaultChart) {
    if (!registeredModes.has(config.defaultChart)) {
      addError(result, {
        code: "CONFIG_UNKNOWN_DEFAULT_CHART",
        message: `visualizationConfig.defaultChart '${config.defaultChart}' is not a registered chart type`,
        severity: "error",
        context: { defaultChart: config.defaultChart, availableModes: Array.from(registeredModes) },
      });
    }

    // defaultChart should be in enabledCharts
    if (config.enabledCharts && !config.enabledCharts.includes(config.defaultChart)) {
      addError(result, {
        code: "CONFIG_DEFAULT_NOT_IN_ENABLED",
        message: `visualizationConfig.defaultChart '${config.defaultChart}' is not in enabledCharts`,
        severity: "error",
        context: { defaultChart: config.defaultChart, enabledCharts: config.enabledCharts },
      });
    }
  }

  // Validate chartOrder
  if (config.chartOrder) {
    if (!Array.isArray(config.chartOrder)) {
      addError(result, {
        code: "CONFIG_CHART_ORDER_NOT_ARRAY",
        message: "visualizationConfig.chartOrder must be an array",
        severity: "error",
        context: { chartOrder: config.chartOrder },
      });
    } else {
      for (const chartId of config.chartOrder) {
        if (!registeredModes.has(chartId)) {
          addError(result, {
            code: "CONFIG_UNKNOWN_CHART_IN_ORDER",
            message: `visualizationConfig.chartOrder contains unknown chart type '${chartId}'`,
            severity: "warning",
            context: { chartId, availableModes: Array.from(registeredModes) },
          });
        }
      }

      // chartOrder should contain all enabledCharts
      if (config.enabledCharts) {
        const missingFromOrder = config.enabledCharts.filter((id) => !config.chartOrder?.includes(id));
        if (missingFromOrder.length > 0) {
          addError(result, {
            code: "CONFIG_ENABLED_NOT_IN_ORDER",
            message: `visualizationConfig.chartOrder is missing enabled charts: ${missingFromOrder.join(", ")}`,
            severity: "warning",
            context: { missingFromOrder },
          });
        }
      }
    }
  }

  return result;
}

// ============================================================================
// Result Data Validation (Runtime)
// ============================================================================

/**
 * Validate result data has required fields for chart rendering
 */
export function validateResultData(result: Result): ValidationResult {
  const validationResult = createResult();

  if (!result) {
    addError(validationResult, {
      code: "RESULT_NULL",
      message: "Result data is null or undefined",
      severity: "error",
      context: {},
    });
    return validationResult;
  }

  if (!Array.isArray(result.clusters)) {
    addError(validationResult, {
      code: "RESULT_CLUSTERS_NOT_ARRAY",
      message: "Result.clusters must be an array",
      severity: "error",
      context: { clusters: result.clusters },
    });
  } else if (result.clusters.length === 0) {
    addError(validationResult, {
      code: "RESULT_NO_CLUSTERS",
      message: "Result.clusters is empty - charts may not render correctly",
      severity: "warning",
      context: {},
    });
  } else {
    // Validate cluster structure
    for (let i = 0; i < Math.min(result.clusters.length, 5); i++) {
      const cluster = result.clusters[i];
      if (!cluster.id) {
        addError(validationResult, {
          code: "CLUSTER_MISSING_ID",
          message: `Cluster at index ${i} is missing 'id' field`,
          severity: "error",
          context: { index: i, cluster },
        });
      }
      if (cluster.level === undefined) {
        addError(validationResult, {
          code: "CLUSTER_MISSING_LEVEL",
          message: `Cluster '${cluster.id}' is missing 'level' field`,
          severity: "error",
          context: { clusterId: cluster.id },
        });
      }
    }
  }

  if (!Array.isArray(result.arguments)) {
    addError(validationResult, {
      code: "RESULT_ARGUMENTS_NOT_ARRAY",
      message: "Result.arguments must be an array",
      severity: "error",
      context: { arguments: result.arguments },
    });
  }

  return validationResult;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format validation result for console output
 */
export function formatValidationResult(result: ValidationResult): string {
  const lines: string[] = [];

  if (result.valid && result.warnings.length === 0) {
    return "✓ Validation passed";
  }

  if (result.errors.length > 0) {
    lines.push(`✗ ${result.errors.length} error(s):`);
    for (const error of result.errors) {
      lines.push(`  [${error.code}] ${error.message}`);
    }
  }

  if (result.warnings.length > 0) {
    lines.push(`⚠ ${result.warnings.length} warning(s):`);
    for (const warning of result.warnings) {
      lines.push(`  [${warning.code}] ${warning.message}`);
    }
  }

  return lines.join("\n");
}

/**
 * Throw an error if validation fails (for strict mode)
 */
export function assertValidation(result: ValidationResult, context: string): void {
  if (!result.valid) {
    const errorMessages = result.errors.map((e) => `[${e.code}] ${e.message}`).join("\n");
    throw new Error(`${context} validation failed:\n${errorMessages}`);
  }
}

/**
 * Log validation warnings to console
 */
export function logValidationWarnings(result: ValidationResult, context: string): void {
  if (result.warnings.length > 0) {
    console.warn(`${context} validation warnings:\n${formatValidationResult({ ...result, errors: [] })}`);
  }
}
