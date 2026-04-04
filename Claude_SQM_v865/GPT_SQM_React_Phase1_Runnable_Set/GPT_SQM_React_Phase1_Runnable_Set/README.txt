# GPT_SQM_React_Phase1_Frontend_Set

포함 파일
- api/main.py
- api/dashboard_read_service.py
- web/src/pages/InventoryPage.jsx (client.js 사용하도록 패치)
- web/src/pages/DashboardPage.jsx
- web/src/api/client.js
- web/vite.config.js

실행 예시
1) FastAPI
   uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

2) React(Vite)
   npm install
   npm install vite @vitejs/plugin-react react react-dom
   npm run dev
