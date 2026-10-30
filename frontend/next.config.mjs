/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    allowedDevOrigins: [
      "192.168.137.1",
      "192.168.137.1:3000",
      "10.3.8.139",
      "10.3.8.139:3000",
      "localhost:3000",
      "127.0.0.1:3000",
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;

