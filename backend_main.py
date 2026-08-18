"""Docker/서비스용 백엔드 진입점.

Windows GUI 진입점(main_webview.py)과 분리해서 사용한다.
"""

from backend.api import app


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info", access_log=True)


if __name__ == "__main__":
    main()
