const path = require("path");
require("dotenv").config();

module.exports = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: { "@": path.resolve(__dirname, "src") },
    configure: (webpackConfig) => {
      webpackConfig.watchOptions = {
        ...webpackConfig.watchOptions,
        ignored: ["**/node_modules/**", "**/.git/**", "**/build/**", "**/dist/**", "**/coverage/**", "**/public/**"],
      };
      return webpackConfig;
    },
  },
  devServer: (devServerConfig) => {
    const { https, onAfterSetupMiddleware, onBeforeSetupMiddleware, onListening, setupMiddlewares, ...rest } = devServerConfig;
    const compatible = { ...rest };
    if (https !== undefined) compatible.server = https === true ? "https" : https ? { type: "https", options: https } : "http";
    compatible.setupMiddlewares = (middlewares, devServer) => {
      if (onBeforeSetupMiddleware) onBeforeSetupMiddleware(devServer);
      if (setupMiddlewares) middlewares = setupMiddlewares(middlewares, devServer);
      if (onAfterSetupMiddleware) onAfterSetupMiddleware(devServer);
      return middlewares;
    };
    if (onListening) compatible.onListening = onListening;
    return compatible;
  },
};
