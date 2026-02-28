// metro.config.js
const { getDefaultConfig } = require("expo/metro-config");
const path = require('path');
const { FileStore } = require('metro-cache');

const config = getDefaultConfig(__dirname);

// Use a stable on-disk store (shared across web/android)
const root = process.env.METRO_CACHE_ROOT || path.join(__dirname, '.metro-cache');
config.cacheStores = [
  new FileStore({ root: path.join(root, 'cache') }),
];

// Add font file extensions for proper bundling
config.resolver.assetExts = [...(config.resolver.assetExts || []), 'ttf', 'otf', 'woff', 'woff2'];

// Disable watchman to avoid file watcher limits in containerized environments
config.resolver.useWatchman = false;

// Ensure node_modules resolution works correctly for babel plugins
config.resolver.nodeModulesPaths = [path.resolve(__dirname, 'node_modules')];

// Disable file watching in CI/containerized environments
if (process.env.CI === 'true' || process.env.CI === '1') {
  config.watcher = {
    healthCheck: {
      enabled: false,
    },
  };
}

// Reduce the number of workers to decrease resource usage
config.maxWorkers = 2;

module.exports = config;
