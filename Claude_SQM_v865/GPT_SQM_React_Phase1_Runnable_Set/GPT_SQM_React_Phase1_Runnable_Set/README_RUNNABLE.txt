SQM React Phase 1 Runnable Set
==============================

추가 파일:
- web/src/App.jsx
- web/src/main.jsx
- web/package.json
- web/index.html

실행 순서
---------
1) FastAPI 실행
   uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

2) React 실행
   cd web
   npm install
   npm run dev

기본 주소
---------
- React: http://127.0.0.1:5173
- Dashboard: http://127.0.0.1:5173/dashboard
- Inventory: http://127.0.0.1:5173/inventory

주의
----
- 이번 세트는 조회 전용 초안입니다.
- 기존 tkinter write-path는 포함하지 않습니다.
- api/main.py와 engine_modules.database import가 동작하려면 SQM 프로젝트 루트 내부에서 실행해야 합니다.
