# SQM 운영 체크리스트
# 생성일: 2026-04-08
# PC 앞에 앉으면 이 순서대로 실행

================================================================
## STEP 1. 배포 (5분)
================================================================

□ SQM_P2BC_DEPLOY.zip 다운로드
□ 압축 해제 → deploy 폴더 생성
□ deploy.bat 더블클릭 → 자동 배치
□ 오류 없이 완료 확인

================================================================
## STEP 2. 테스트 (5분)
================================================================

□ verify.bat 더블클릭
□ pytest 27개 TC 전부 통과 확인
□ 실패 시 → p2b_test_result.txt 루비에게 전달

================================================================
## STEP 3. 서비스 시작 (5분)
================================================================

```bash
cd D:\program\Sqm jaego\Claude_SQM_v871

# 기존 API 서버 (이미 실행 중이면 restart)
pm2 restart sqm-api  또는  pm2 start run_react_api.py --name sqm-api

# 신규 서비스 등록
pm2 start scripts\backup_scheduler.py --interpreter python --name sqm-backup
pm2 start scripts\sqm_bot.py          --interpreter python --name sqm-bot
pm2 save
pm2 list   ← 3개 모두 online 확인
```

================================================================
## STEP 4. Telegram 봇 테스트 (3분)
================================================================

@Claude_kdnbot 에서 순서대로 테스트:

□ /도움말    → 명령어 목록 표시 확인
□ /상태      → API ✅ 정상 + DB ✅ 정상 확인
□ /재고      → 재고 현황 표시 확인
□ /출고      → 오늘 출고 현황 표시 확인
□ /대기      → RESERVED/PICKED 현황 표시 확인
□ /백업      → 백업 완료 메시지 확인

================================================================
## STEP 5. 모바일 UI 연결 (10분)
================================================================

```bash
cd D:\program\Sqm jaego\Claude_SQM_v871\web

# App.jsx 패치 적용 (배포된 App_patched.jsx 복사)
copy deploy\web\src\App.jsx src\App.jsx

# vite.config.js 교체
copy deploy\web\vite.config.js vite.config.js

# MobileDashboard, BarcodeScanner 복사 (이미 배치됨)

# 개발 서버 재시작
npm run dev
```

□ http://[내IP]:5173/mobile 접속 → 모바일 대시보드 표시 확인
□ 스마트폰에서 같은 URL 접속 → 모바일 화면 확인

================================================================
## STEP 6. 운영 연결 패치 (5분)
================================================================

아래 3개 패치 적용:

### PATCH C (가장 중요 — 즉시 효과)
engine_modules/database.py 의 SQMDatabase.__init__ 마지막에 추가:
```python
try:
    from engine_modules.db_optimize import run_db_optimize
    run_db_optimize(self)
except Exception as e:
    pass
```

### PATCH B (db.py에 헬퍼 추가)
react_api/utils/db.py 하단에 추가:
```python
def get_inventory_repo():
    from features.repositories.inventory_repository import InventoryRepository
    return InventoryRepository(_get_shared_db())
```

### outbound_write.py에 confirm 엔드포인트 추가
react_api/routes/outbound_write.py 하단에 추가:
```python
class OutboundConfirmRequest(BaseModel):
    lot_no: str
    force_all: bool = False

@router.post("/confirm", response_model=WriteResponse)
def outbound_confirm(req: OutboundConfirmRequest) -> WriteResponse:
    try:
        with get_engine() as engine:
            from features.services.outbound_service import OutboundService
            svc = OutboundService(engine.db)
            result = svc.confirm_outbound(lot_no=req.lot_no, force_all=req.force_all)
        return WriteResponse(
            success=result["success"],
            message=f"확정: {result['confirmed']}건" if result["success"]
                    else "; ".join(result["errors"][:2]),
            data=result
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))
```

================================================================
## STEP 7. PWA 설치 (선택, 5분)
================================================================

```bash
cd web
npm install -D vite-plugin-pwa
```

vite.config.js 에서 VitePWA 주석 해제 후:
```bash
npm run build
```

스마트폰 크롬에서:
□ http://[내IP]:5173/mobile 접속
□ 브라우저 메뉴 → "홈 화면에 추가"
□ SQM 아이콘 생성 확인

================================================================
## STEP 8. 자동 백업 동작 확인
================================================================

```bash
# 즉시 백업 테스트
python scripts\backup_scheduler.py --now
```

□ 백업 완료 메시지 확인
□ @Claude_kdnbot 에 ✅ 백업 완료 메시지 수신 확인
□ data\backup 폴더에 백업 파일 생성 확인

================================================================
## 완료 기준
================================================================

□ pm2 list → sqm-api, sqm-backup, sqm-bot 모두 online
□ /mobile URL 스마트폰 접속 성공
□ pytest 27개 TC 통과
□ @Claude_kdnbot /재고 명령어 응답
□ 자동 백업 정상 동작

→ 모두 체크 완료 시 P2-B+C+개선 전체 운영 완료 ✅
