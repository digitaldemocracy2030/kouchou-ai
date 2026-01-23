/**
 * Chart Plugins Index
 *
 * Export all chart plugin components and utilities.
 */

// Types
export type {
  ChartPlugin,
  ChartPluginManifest,
  ChartMode,
  ChartRenderContext,
  ChartComponentProps,
  ScatterChartProps,
  TreemapChartProps,
  AnyChartProps,
} from "./types";

// Registry
export { ChartPluginRegistry, chartRegistry, loadBuiltinChartPlugins, ensurePluginsLoaded } from "./registry";

// Validation
export {
  validatePlugin,
  validatePluginManifest,
  validateChartMode,
  validateVisualizationConfig,
  validateResultData,
  formatValidationResult,
  assertValidation,
  logValidationWarnings,
} from "./validation";
export type { ValidationError, ValidationResult } from "./validation";

// Built-in plugins
export { scatterPlugin } from "./scatter";
export { treemapPlugin } from "./treemap";
export { hierarchyListPlugin } from "./hierarchy-list";
