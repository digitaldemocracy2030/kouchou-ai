/**
 * Chart Plugin Registry
 *
 * Central registry for chart visualization plugins.
 * Similar to PluginRegistry in apps/api/src/plugins/registry.py
 */

import type { ChartMode, ChartPlugin } from "./types";

class ChartPluginRegistry {
  private plugins: Map<string, ChartPlugin> = new Map();
  private modeToPlugin: Map<string, ChartPlugin> = new Map();

  /**
   * Register a chart plugin
   */
  register(plugin: ChartPlugin): void {
    this.plugins.set(plugin.manifest.id, plugin);

    // Map each mode to this plugin for quick lookup
    for (const mode of plugin.manifest.modes) {
      this.modeToPlugin.set(mode.id, plugin);
    }

    console.debug(`Registered chart plugin: ${plugin.manifest.id} (v${plugin.manifest.version})`);
  }

  /**
   * Get a plugin by its ID
   */
  get(pluginId: string): ChartPlugin | undefined {
    return this.plugins.get(pluginId);
  }

  /**
   * Get the plugin that handles a specific mode
   */
  getByMode(modeId: string): ChartPlugin | undefined {
    return this.modeToPlugin.get(modeId);
  }

  /**
   * Get all registered plugins
   */
  getAll(): ChartPlugin[] {
    return Array.from(this.plugins.values());
  }

  /**
   * Get all chart modes from all plugins in order
   */
  getAllModes(): ChartMode[] {
    const modes: ChartMode[] = [];
    for (const plugin of this.plugins.values()) {
      modes.push(...plugin.manifest.modes);
    }
    return modes;
  }

  /**
   * Check if a mode is registered
   */
  hasMode(modeId: string): boolean {
    return this.modeToPlugin.has(modeId);
  }

  /**
   * Clear all registered plugins (for testing)
   */
  clear(): void {
    this.plugins.clear();
    this.modeToPlugin.clear();
  }
}

// Global singleton instance
export const chartRegistry = new ChartPluginRegistry();

/**
 * Load all built-in chart plugins
 * Called during application initialization
 */
export function loadBuiltinChartPlugins(): void {
  // Import and register built-in plugins
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { scatterPlugin } = require("./scatter");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { treemapPlugin } = require("./treemap");

  chartRegistry.register(scatterPlugin);
  chartRegistry.register(treemapPlugin);

  console.debug(`Loaded ${chartRegistry.getAll().length} chart plugins`);
}

// Auto-initialize on module load
let initialized = false;

export function ensurePluginsLoaded(): void {
  if (!initialized) {
    loadBuiltinChartPlugins();
    initialized = true;
  }
}
