"""
SQM Inventory — PyWebView 진입점 (Tkinter 대체)
실행: python main_webview.py
"""
import threading
import time
import os
import sys
import logging

# PyInstaller frozen exe (console=False) 에서 stdout/stderr가 None →
# logging StreamHandler가 터지는 것을 방지: 로그 파일로 리다이렉트
if getattr(sys, 'frozen', False) and sys.stdout is None:
    _log_path = os.path.join(os.path.dirname(sys.executable), 'sqm_webview.log')
    _log_file = open(_log_path, 'a', encoding='utf-8', buffering=1)
    sys.stdout = _log_file
    sys.stderr = _log_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
API_HOST = '127.0.0.1'
API_PORT = 8765

def run_api_server():
    """FastAPI 서버를 별도 스레드에서 실행"""
    try:
        import uvicorn
        from backend.api import app
        uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="warning")
    except Exception as e:
        log.error(f"API 서버 시작 실패: {e}")

def is_port_open(host, port):
    """TCP 소켓이 LISTEN 상태인지 (다른 프로세스가 점유 중인지) 확인"""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try: s.close()
        except Exception: pass

def kill_zombie_on_port(port):
    """
    Windows 한정: 해당 포트를 LISTEN 하는 프로세스(좀비) 를 종료.
    이전 세션에서 창 X 로 닫고 프로세스가 살아남은 경우 재실행을 가능하게 함.
    """
    if os.name != 'nt':
        return False
    import subprocess, re
    try:
        out = subprocess.check_output(
            ['netstat', '-ano', '-p', 'tcp'],
            text=True, encoding='cp949', errors='ignore'
        )
    except Exception as e:
        log.warning(f"netstat 실패: {e}")
        return False
    killed = False
    for line in out.splitlines():
        if f':{port}' not in line or 'LISTENING' not in line:
            continue
        parts = re.split(r'\s+', line.strip())
        if not parts:
            continue
        pid = parts[-1]
        if not pid.isdigit():
            continue
        # 자기 자신 PID 는 건너뛰기
        if int(pid) == os.getpid():
            continue
        log.warning(f"좀비 uvicorn 감지 (PID={pid}, port={port}) → 종료 시도")
        try:
            subprocess.run(['taskkill', '/F', '/PID', pid],
                           check=False, timeout=5,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            killed = True
        except Exception as e:
            log.error(f"taskkill PID={pid} 실패: {e}")
    if killed:
        time.sleep(0.7)  # OS 가 포트 놓을 시간
    return killed

def wait_for_api(timeout=10):
    """API 서버가 준비될 때까지 대기. /api/health 없으면 루트 '/' 로 폴백."""
    import urllib.request
    deadline = time.time() + timeout
    probes = [f'http://{API_HOST}:{API_PORT}/api/health',
              f'http://{API_HOST}:{API_PORT}/']
    while time.time() < deadline:
        for url in probes:
            try:
                urllib.request.urlopen(url, timeout=1)
                log.info(f"API 서버 준비 완료 ({url})")
                return True
            except Exception:
                pass
        time.sleep(0.3)
    log.warning("API 서버 연결 타임아웃 — 오프라인 모드로 진행")
    return False

def main():
    # 0. 포트 사전 점검: 점유 중이면 좀비 종료
    if is_port_open(API_HOST, API_PORT):
        log.warning(f"포트 {API_PORT} 선점 상태 → 좀비 uvicorn 제거")
        kill_zombie_on_port(API_PORT)
        if is_port_open(API_HOST, API_PORT):
            log.error(
                f"포트 {API_PORT} 가 여전히 점유됨. 수동 확인 필요:\n"
                f'  netstat -ano | findstr :{API_PORT}'
            )

    # 1. API 서버 시작 (백그라운드 스레드)
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    log.info(f"API 서버 시작 중 (http://{API_HOST}:{API_PORT})")

    # 2. API 준비 대기
    wait_for_api()

    # 3. PyWebView 창 생성
    try:
        import webview

        index_path = os.path.join(FRONTEND_DIR, 'index.html')
        if not os.path.exists(index_path):
            log.error(f"index.html 없음: {index_path}")
            sys.exit(1)

        # ⚠️ ESM import 가 file:// 에서 CORS 차단되므로 http://127.0.0.1:8765/ 로 서빙
        # FastAPI 가 frontend/ 를 정적 mount 하도록 backend/api.py 에 추가됨
        url = f'http://{API_HOST}:{API_PORT}/'

        window = webview.create_window(
            title='SQM Inventory v8.6.4.3 — 광양창고',
            url=url,
            width=1400,
            height=900,
            min_size=(1024, 700),
            resizable=True,
            background_color='#070e1a',
        )

        def on_loaded():
            # JS 브릿지 초기화
            window.evaluate_js(f'''
                window.SQM_API_BASE = "http://{API_HOST}:{API_PORT}";
                console.log("[SQM] API Base:", window.SQM_API_BASE);
            ''')

        window.events.loaded += on_loaded

        log.info("PyWebView 창 시작 (DEBUG MODE — 우클릭 → 검사로 콘솔 확인 가능)")
        webview.start(debug=True)

    except ImportError:
        log.error("pywebview 미설치. 설치: pip install pywebview")
        # 폴백: 기본 브라우저로 열기
        import webbrowser
        index_path = os.path.join(FRONTEND_DIR, 'index.html')
        webbrowser.open(f'file:///{index_path}')
        input("브라우저 모드로 실행됨. 종료하려면 Enter...")
    except Exception as e:
        log.exception(f"PyWebView 실행 실패: {e}")

if __name__ == '__main__':
    main()
