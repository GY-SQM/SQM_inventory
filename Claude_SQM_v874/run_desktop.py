#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQM Desktop App — pywebview 기반
★ React UI를 브라우저 없이 네이티브 창으로 실행
★ 내부적으로 FastAPI 서버 자동 시작
★ 창 닫으면 서버도 자동 종료

실행: python run_desktop.py
빌드: pyinstaller sqm_web_desktop.spec
"""
import os
import sys
import time
import threading
import logging
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── pythonw 대응: stdout/stderr/원본 전부 파일로 리다이렉트 ──
_null_log = ROOT / 'logs' / 'sqm_stdout.log'
_null_log.parent.mkdir(parents=True, exist_ok=True)
_log_stream = open(str(_null_log), 'w', encoding='utf-8')
sys.stdout = _log_stream
sys.stderr = _log_stream
sys.__stdout__ = _log_stream
sys.__stderr__ = _log_stream

# .env 로드
env_file = ROOT / '.env'
if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# ── 로그 설정: CMD 화면은 완전 숨김, 파일에만 기록 ──
_log_file = ROOT / 'logs' / 'sqm_desktop.log'
_log_file.parent.mkdir(parents=True, exist_ok=True)

# 모든 기존 핸들러 제거 후 파일 핸들러만 설정
_root_logger = logging.getLogger()
_root_logger.handlers.clear()
_root_logger.setLevel(logging.INFO)

_file_handler = logging.FileHandler(str(_log_file), encoding='utf-8')
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))
_root_logger.addHandler(_file_handler)

# CMD 콘솔에는 CRITICAL만 (사실상 아무것도 안 나옴)
_console = logging.StreamHandler()
_console.setLevel(logging.CRITICAL)
_root_logger.addHandler(_console)

# uvicorn 로거도 강제 억제
for _ln in ('uvicorn', 'uvicorn.error', 'uvicorn.access', 'uvicorn.asgi',
            'react_api', 'engine_modules', 'sqm', 'httpx', 'httpcore',
            'fastapi', 'starlette', '__main__', 'root'):
    _l = logging.getLogger(_ln)
    _l.handlers.clear()
    _l.addHandler(_file_handler)
    _l.propagate = False

logger = logging.getLogger(__name__)

API_HOST = os.getenv('API_HOST', '127.0.0.1')


def _find_free_port(host: str, preferred: int = 8000) -> int:
    """빈 포트 자동 탐색 — preferred 포트 사용 가능하면 그대로, 아니면 빈 포트 할당"""
    import socket
    # 1) 선호 포트 먼저 시도
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, preferred))
            return preferred
        except OSError:
            pass
    # 2) OS가 빈 포트 자동 할당
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        port = s.getsockname()[1]
    return port


_preferred = int(os.getenv('API_PORT', '8000'))
API_PORT = _find_free_port(API_HOST, _preferred)
API_URL  = f'http://{API_HOST}:{API_PORT}'

if API_PORT != _preferred:
    logger.info(f"포트 {_preferred} 사용 중 → 빈 포트 {API_PORT} 자동 할당")

# ================================================================
# FastAPI 서버 — 백그라운드 스레드로 실행
# ================================================================
_server_ready = threading.Event()

def _start_api_server():
    """백그라운드에서 FastAPI + uvicorn 실행"""
    try:
        import uvicorn
        from react_api.main import app

        logger.info(f"FastAPI 서버 시작: {API_URL}")

        # 시작 완료 신호
        def on_startup():
            _server_ready.set()
            logger.info("FastAPI 준비 완료")

        # uvicorn 설정 — CMD 콘솔 출력 완전 차단
        config = uvicorn.Config(
            app,
            host=API_HOST,
            port=API_PORT,
            log_level='critical',     # 콘솔 로그 완전 차단
            access_log=False,
        )
        server = uvicorn.Server(config)

        # startup 이벤트 후 신호 발송
        original_startup = server.startup
        async def patched_startup(*args, **kwargs):
            await original_startup(*args, **kwargs)
            _server_ready.set()

        server.startup = patched_startup
        server.run()

    except Exception as e:
        logger.error(f"API 서버 시작 실패: {e}")
        _server_ready.set()  # 실패해도 대기 해제


def _wait_for_server(timeout: int = 15) -> bool:
    """서버 준비 대기"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f'{API_URL}/api/health', timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


# ================================================================
# pywebview 창 실행
# ================================================================
def _run_browser_fallback():
    """pywebview 없을 때 브라우저로 자동 전환"""
    import webbrowser
    import subprocess

    logger.info("pywebview 없음 → 브라우저 모드로 전환")
    print("\n⚠️  pywebview 미설치 → 브라우저 모드로 실행합니다.")
    print("   (네이티브 창을 원하면: pip install pywebview)\n")

    server_thread = threading.Thread(target=_start_api_server, daemon=True)
    server_thread.start()

    if _wait_for_server(timeout=20):
        logger.info("서버 준비 완료 — 브라우저 열기")
        web_dir = ROOT / 'web'
        vite_proc = subprocess.Popen(
            ['npx', 'vite', '--host', '0.0.0.0', '--port', '5173'],
            cwd=str(web_dir), shell=True,
        )
        time.sleep(3)
        webbrowser.open('http://localhost:5173')
        print("✅ 브라우저에서 http://localhost:5173 열림")
        print("   종료하려면 Ctrl+C를 누르세요.\n")
        try:
            vite_proc.wait()
        except KeyboardInterrupt:
            vite_proc.terminate()
            print("\n종료됨.")
    else:
        print("❌ 서버 시작 실패")
        input("엔터를 누르면 종료됩니다...")
        sys.exit(1)


def run_desktop():
    """pywebview 창으로 React UI 실행 (없으면 자동설치 시도 → 브라우저 폴백)"""
    try:
        import webview
    except ImportError:
        logger.info("pywebview 미설치 → 자동 설치 시도")
        print("⏳ pywebview 자동 설치 중...")
        import subprocess as _sp
        result = _sp.run([sys.executable, '-m', 'pip', 'install', 'pywebview'],
                         capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pywebview 설치 완료!")
            import webview
        else:
            _run_browser_fallback()
            return

    # ── 1) FastAPI 서버 백그라운드 시작 ──────────────────────────
    # CMD 출력 (pythonw로 실행 시 무시됨)
    try:
        print()
        print('  SQM v8.7.4 시작 중...')
        print()
    except Exception:
        pass
    server_thread = threading.Thread(target=_start_api_server, daemon=True)
    server_thread.start()

    # ── 2) 로딩 창 표시 (서버 준비 중) ──────────────────────────
    loading_html = """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { margin:0; background:#0f172a; display:flex; align-items:center;
               justify-content:center; height:100vh; font-family:'Segoe UI',sans-serif;
               overflow:hidden; }
        .wrap { text-align:center; color:#f1f5f9; width:500px; }
        .logo { font-size:64px; margin-bottom:20px; }
        .title { font-size:28px; font-weight:700; margin-bottom:6px; letter-spacing:0.05em; }
        .ver { font-size:14px; color:#64748b; margin-bottom:48px; }
        .bar-bg { width:100%; height:8px; background:#1e293b; border-radius:4px;
                  overflow:hidden; }
        .bar-fill { height:100%; border-radius:4px; width:0%;
                    background:linear-gradient(90deg,#3b82f6,#38bdf8,#22d3ee);
                    background-size:200% 100%;
                    animation:shimmer 1.5s ease-in-out infinite;
                    transition:width 0.4s ease; }
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        .status { font-size:13px; color:#64748b; margin-top:12px; min-height:20px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="logo">📦</div>
        <div class="title">SQM 재고관리</div>
        <div class="ver">v8.7.4</div>
        <div class="bar-bg"><div class="bar-fill" id="bar"></div></div>
        <div class="status" id="status">시스템 시작 중...</div>
      </div>
      <script>
        const steps = [
          [8,  '환경 설정 로드...'],
          [20, '데이터베이스 연결...'],
          [35, '스키마 검증...'],
          [50, '마이그레이션 확인...'],
          [65, 'API 서버 시작...'],
          [78, '라우터 등록...'],
          [88, 'React UI 로드...'],
          [95, '최종 준비...'],
        ];
        let i = 0;
        function tick() {
          if (i < steps.length) {
            document.getElementById('bar').style.width = steps[i][0] + '%';
            document.getElementById('status').textContent = steps[i][1];
            i++;
            setTimeout(tick, 700 + Math.random() * 500);
          } else {
            document.getElementById('bar').style.width = '100%';
            document.getElementById('status').textContent = '시작 완료!';
          }
        }
        setTimeout(tick, 200);
      </script>
    </body>
    </html>
    """

    # ── 3) pywebview 창 생성 ─────────────────────────────────────
    window = webview.create_window(
        title='SQM 재고관리 v8.7.4',
        html=loading_html,
        width=1400,
        height=900,
        min_size=(1024, 768),
        resizable=True,
        shadow=True,
        text_select=True,
    )

    def on_shown():
        """창이 표시된 후 서버 대기 → React URL로 전환"""
        if _wait_for_server(timeout=20):
            logger.info("서버 준비 완료 — React 로드")
            window.load_url(f'{API_URL}')
        else:
            window.load_html("""
            <div style="padding:40px;background:#0f172a;color:#ef4444;font-family:sans-serif;text-align:center">
              <h2>❌ 서버 시작 실패</h2>
              <p style="color:#94a3b8">FastAPI 서버가 응답하지 않습니다.</p>
              <p style="color:#94a3b8">react_api/ 폴더와 .env 파일을 확인하세요.</p>
            </div>
            """)

    webview.start(on_shown, debug=False)
    logger.info("SQM Desktop 종료")


# ================================================================
# 진입점
# ================================================================
if __name__ == '__main__':
    try:
        run_desktop()
    except Exception as e:
        import traceback
        print("\n" + "=" * 60)
        print("  [ERROR] SQM Desktop 실행 중 오류 발생")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        print(f"  원인: {type(e).__name__}: {e}")
        print("  위 에러 로그를 확인한 후 아무 키나 누르면 종료됩니다.")
        print("=" * 60)
        input("  >>> 아무 키나 누르세요... ")
