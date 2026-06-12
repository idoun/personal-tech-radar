import type { NextConfig } from 'next';

const isProdServer = process.env.TECHNEWS_FRONTEND_PROFILE === 'prod';

const nextConfig: NextConfig = {
  basePath: '/technews',
  trailingSlash: true,
  distDir: isProdServer ? '.next-prod' : '.next',
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
