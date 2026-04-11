# -*- coding: utf-8 -*-
"""
SQM React Phase1 API 실행 진입점.

사용법:
    python run_react_api.py              # 구조화된 react_api 패키지 실행 (기본)
    python run_react_api.py --draft      # GPT_SQM_React_Phase1_Draft 버전 실행

v866 루트에서 실행해야 engine_modules import가 정상 동작합니다.
"""
import sys
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# .env 파일 자동 로드 (run_desktop.py와 동일한 방식)
_env_file = os.path.join(ROOT_DIR, '.env')
if os.path.exists(_env_file):
    with open(_env_file, encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())


def main():
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn이 설치되어 있지 않습니다.")
        print("  pip install uvicorn[standard] fastapi")
        sys.exit(1)

    # --draft 플래그: GPT_SQM_React_Phase1_Draft 버전 사용
    use_draft = "--draft" in sys.argv

    if use_draft:
        draft_dir = os.path.join(ROOT_DIR, "GPT_SQM_React_Phase1_Draft")
        if draft_dir not in sys.path:
            sys.path.insert(0, draft_dir)
        app_module = "api.main:app"
        reload_dirs = [draft_dir]
        print(f"[SQM React API] Mode: Draft (GPT_SQM_React_Phase1_Draft)")
    else:
        app_module = "react_api.main:app"
        reload_dirs = [os.path.join(ROOT_DIR, "react_api")]
        print(f"[SQM React API] Mode: Structured (react_api/)")

    print(f"[SQM React API] ROOT: {ROOT_DIR}")
    print("[SQM React API] 서버 시작 중...")
    print("[SQM React API] Docs: http://127.0.0.1:8000/docs")

    # host="0.0.0.0" → 같은 네트워크(LAN) 모든 기기에서 접속 가능
    # 핸드폰/태블릿/다른 PC → http://[이 PC의 IP]:8000 으로 접속
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))

    # 접속 가능한 주소 안내
    import socket
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "알수없음"

    print(f"[SQM React API] 로컬 접속  : http://localhost:{port}")
    print(f"[SQM React API] LAN 접속   : http://{local_ip}:{port}")
    print(f"[SQM React API] 같은 와이파이의 모든 기기에서 위 LAN 주소로 접속 가능")

    uvicorn.run(
        app_module,
        host=host,
        port=port,
        reload=False,          # 운영 모드 — reload 끔 (성능/안정성)
        workers=1,             # SQLite 단일 프로세스 유지
        access_log=True,
    )


if __name__ == "__main__":
    main()
