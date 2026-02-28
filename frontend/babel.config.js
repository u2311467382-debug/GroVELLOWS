module.exports = function(api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      // Only include reanimated plugin for native builds, not web
      ...(process.env.EXPO_WEB !== 'true' ? ['react-native-reanimated/plugin'] : []),
    ],
  };
};
