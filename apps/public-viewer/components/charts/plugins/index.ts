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
export { chartRegistry, loadBuiltinChartPlugins, ensurePluginsLoaded } from "./registry";

// Built-in plugins
export { scatterPlugin } from "./scatter";
export { treemapPlugin } from "./treemap";
