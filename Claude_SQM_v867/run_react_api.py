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
    print("[SQM React API] Starting on http://127.0.0.1:8000")
    print("[SQM React API] Docs: http://127.0.0.1:8000/docs")

    uvicorn.run(
        app_module,
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=reload_dirs,
    )


if __name__ == "__main__":
    main()
