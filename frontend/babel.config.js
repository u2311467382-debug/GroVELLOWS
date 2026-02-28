module.exports = function(api) {
  api.cache(true);
  return {
    presets: [
      [
        'babel-preset-expo',
        {
          // Disable the react-native-reanimated plugin
          'react-native-reanimated': false,
        },
      ],
    ],
  };
};
