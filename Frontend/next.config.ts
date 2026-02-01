import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Output configuration for production deployment
  output: 'standalone',
  
  // Allow OAuth popups to communicate with parent window
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin-allow-popups',
          },
        ],
      },
    ];
  },
};

export default nextConfig;

