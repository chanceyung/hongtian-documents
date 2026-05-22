import type { NextConfig } from 'next'

const isStatic = process.env.BUILD_TARGET === 'desktop'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 桌面版：静态 HTML 导出（无需 Node 运行时）
  // Web/Docker 版：standalone（需要 Node 运行时）
  output: isStatic ? 'export' : 'standalone',
  images: {
    unoptimized: true,
  },
  // 静态导出不需要 basePath
  trailingSlash: false,
}

export default nextConfig