# App.jsx 모바일 라우터 추가 패치
# 배치일: 2026-04-08
# 대상: web/src/App.jsx

## 1. import 추가 (파일 상단)
```jsx
import MobileDashboard from './pages/MobileDashboard';
import BarcodeScanner from './components/BarcodeScanner';
```

## 2. 라우터에 경로 추가
App.jsx의 Routes 블록에 아래 추가:
```jsx
{/* 모바일 전용 화면 */}
<Route path="/mobile"   element={<MobileDashboard />} />
<Route path="/scan-mobile" element={<BarcodeScanner />} />
```

## 3. MenuBar에 모바일 메뉴 추가
MenuBar.jsx에서 모바일 접속 시 하단 네비 표시:
```jsx
// 모바일 감지
const isMobile = window.innerWidth < 768;
if (isMobile) return <MobileDashboard />;
```

## 4. 접속 URL
- 모바일 대시보드: http://[서버IP]:5173/mobile
- 바코드 스캔:     http://[서버IP]:5173/scan-mobile

## 5. PWA 설정 (선택) — vite.config.js
npm install vite-plugin-pwa 후:
```js
import { VitePWA } from 'vite-plugin-pwa'
plugins: [
  VitePWA({
    registerType: 'autoUpdate',
    manifest: {
      name: 'SQM 현장 관리',
      short_name: 'SQM',
      theme_color: '#0f172a',
      display: 'standalone',
      icons: [{ src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml' }]
    }
  })
]
```
→ 안드로이드 크롬에서 "홈 화면에 추가" 가능
