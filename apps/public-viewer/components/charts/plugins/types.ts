/**
 * Chart Plugin System Types
 *
 * Defines the interface for chart visualization plugins.
 * Similar to the input plugin pattern in apps/api/src/plugins/base.py
 */

import type { Argument, Cluster, Config, Result } from "@/type";
import type { ComponentType } from "react";

/**
 * Common props passed to all chart components
 */
export interface ChartComponentProps {
  /** List of clusters for visualization */
  clusterList: Cluster[];
  /** List of arguments/opinions */
  argumentList: Argument[];
  /** Callback when hover occurs */
  onHover?: () => void;
  /** IDs of arguments that match current filter (undefined = no filter) */
  filteredArgumentIds?: string[];
  /** Report configuration */
  config?: Config;
}

/**
 * Props specific to scatter-type charts
 */
export interface ScatterChartProps extends ChartComponentProps {
  /** Target hierarchy level to display */
  targetLevel: number;
  /** Whether to show cluster labels */
  showClusterLabels?: boolean;
}

/**
 * Props specific to treemap-type charts
 */
export interface TreemapChartProps extends ChartComponentProps {
  /** Current zoom level in treemap */
  level: string;
  /** Callback when treemap navigation occurs */
  onTreeZoom: (level: string) => void;
}

/**
 * Union type for all chart component props
 */
export type AnyChartProps = ScatterChartProps | TreemapChartProps;

/**
 * Chart plugin manifest - metadata describing the plugin
 */
export interface ChartPluginManifest {
  /** Unique plugin identifier (e.g., "scatter", "treemap") */
  id: string;
  /** Human-readable name for display */
  name: string;
  /** Description of the chart type */
  description: string;
  /** Plugin version (semver) */
  version: string;
  /** Icon component for the chart selector */
  icon: ComponentType;
  /**
   * Chart modes this plugin handles
   * e.g., scatter plugin handles ["scatterAll", "scatterDensity"]
   */
  modes: ChartMode[];
}

/**
 * Chart mode definition - represents a specific view mode
 */
export interface ChartMode {
  /** Mode identifier used in selectedChart state */
  id: string;
  /** Display label for the mode */
  label: string;
  /** Icon component for this mode */
  icon: ComponentType;
  /** Whether this mode can be disabled based on data */
  canBeDisabled?: boolean;
  /** Function to check if mode should be disabled */
  isDisabled?: (result: Result) => boolean;
  /** Tooltip to show when disabled */
  disabledTooltip?: string;
}

/**
 * Context passed to chart components for rendering
 */
export interface ChartRenderContext {
  /** Full result data */
  result: Result;
  /** Currently selected chart mode */
  selectedChart: string;
  /** Whether chart is in fullscreen mode */
  isFullscreen: boolean;
  /** Filtered argument IDs (if filter is active) */
  filteredArgumentIds?: string[];
  /** Whether to show cluster labels (for scatter) */
  showClusterLabels?: boolean;
  /** Current treemap zoom level */
  treemapLevel?: string;
  /** Callback for treemap navigation */
  onTreeZoom?: (level: string) => void;
  /** Callback when hover occurs */
  onHover?: () => void;
}

/**
 * Complete chart plugin definition
 */
export interface ChartPlugin {
  /** Plugin manifest with metadata */
  manifest: ChartPluginManifest;
  /**
   * Render function that returns the appropriate component
   * This allows plugins to handle mode-specific rendering internally
   */
  render: (context: ChartRenderContext) => React.ReactNode;
  /**
   * Check if this plugin can handle the given mode
   */
  canHandle: (mode: string) => boolean;
}
