import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// ★ PWA 추가: npm install -D vite-plugin-pwa
// 설치 후 아래 주석 해제
// import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),

    // ★ PWA 설정 (vite-plugin-pwa 설치 후 활성화)
    // VitePWA({
    //   registerType: 'autoUpdate',
    //   includeAssets: ['favicon.svg', 'icons.svg'],
    //   manifest: {
    //     name: 'SQM 현장 관리',
    //     short_name: 'SQM',
    //     description: 'GY Logistics SQM 재고 관리 시스템',
    //     theme_color: '#0f172a',
    //     background_color: '#0f172a',
    //     display: 'standalone',
    //     orientation: 'portrait',
    //     start_url: '/mobile',
    //     icons: [
    //       { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }
    //     ]
    //   },
    //   workbox: {
    //     // 오프라인 캐시 — API 마지막 응답 캐시
    //     runtimeCaching: [
    //       {
    //         urlPattern: /^\/api\/dashboard/,
    //         handler: 'StaleWhileRevalidate',
    //         options: { cacheName: 'dashboard-cache', expiration: { maxAgeSeconds: 60 } }
    //       },
    //       {
    //         urlPattern: /^\/api\/inventory/,
    //         handler: 'StaleWhileRevalidate',
    //         options: { cacheName: 'inventory-cache', expiration: { maxAgeSeconds: 30 } }
    //       }
    //     ]
    //   }
    // }),
  ],

  // Vitest 테스트 설정
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'dist/', 'src/__tests__/'],
    },
  },

  server: {
    host: '0.0.0.0',        // ★ 추가: LAN에서 스마트폰 접속 허용
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
