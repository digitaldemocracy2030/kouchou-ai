/**
 * Chart Plugin Registry
 *
 * Central registry for chart visualization plugins.
 * Similar to PluginRegistry in apps/api/src/plugins/registry.py
 */

import type { ChartMode, ChartPlugin } from "./types";
import { formatValidationResult, logValidationWarnings, validatePlugin } from "./validation";

export class ChartPluginRegistry {
  private plugins: Map<string, ChartPlugin> = new Map();
  private modeToPlugin: Map<string, ChartPlugin> = new Map();

  constructor(private strictMode = false) {}

  /**
   * Enable strict mode - throws on validation errors and ID collisions
   */
  setStrictMode(strict: boolean): void {
    this.strictMode = strict;
  }

  /**
   * Register a chart plugin with validation
   */
  register(plugin: ChartPlugin): void {
    // Validate plugin before registration
    const validation = validatePlugin(plugin);

    if (!validation.valid) {
      const message = `Plugin '${plugin.manifest.id}' validation failed:\n${formatValidationResult(validation)}`;
      if (this.strictMode) {
        throw new Error(message);
      }
      console.error(message);
      // Continue registration even with errors (for backward compatibility)
    }

    // Log warnings
    logValidationWarnings(validation, `Plugin '${plugin.manifest.id}'`);

    // Check for plugin ID collision
    if (this.plugins.has(plugin.manifest.id)) {
      this.reportCollision(
        `Chart plugin collision: "${plugin.manifest.id}" is already registered.`,
        `Overwriting with new plugin (v${plugin.manifest.version}).`,
      );
    }

    // Check every collision before mutating either lookup.
    for (const mode of plugin.manifest.modes) {
      // Check for mode ID collision
      const existingPlugin = this.modeToPlugin.get(mode.id);
      if (existingPlugin) {
        this.reportCollision(
          `Chart mode collision: "${mode.id}" is already registered by plugin "${existingPlugin.manifest.id}".`,
          `Overwriting with plugin "${plugin.manifest.id}".`,
        );
      }
    }

    this.plugins.set(plugin.manifest.id, plugin);
    for (const mode of plugin.manifest.modes) {
      this.modeToPlugin.set(mode.id, plugin);
    }

    console.debug(`Registered chart plugin: ${plugin.manifest.id} (v${plugin.manifest.version})`);
  }

  private reportCollision(message: string, overwriteMessage: string): void {
    if (this.strictMode) throw new Error(message);
    console.warn(`${message} ${overwriteMessage}`);
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
export const chartRegistry = new ChartPluginRegistry(true);

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
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { hierarchyListPlugin } = require("./hierarchy-list");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { oppositionPlugin } = require("./opposition");

  const plugins: ChartPlugin[] = [scatterPlugin, treemapPlugin, hierarchyListPlugin, oppositionPlugin];
  for (const plugin of plugins) {
    if (chartRegistry.get(plugin.manifest.id) !== plugin) chartRegistry.register(plugin);
  }

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
