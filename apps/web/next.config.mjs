import { createRequire } from 'module';
const require = createRequire(import.meta.url);

/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.output.globalObject = 'self';

      // 确保 Yjs 只有单一实例，避免 "Yjs was already imported" 警告
      // BlockNote 和其他依赖可能会导入不同版本的 Yjs
      config.resolve.alias = {
        ...config.resolve.alias,
        yjs: require.resolve('yjs'),
      };
    }
    return config;
  },
};

export default nextConfig;
