# SQM Docker 분리 실행 문서

## 목적
이 문서는 SQM에서 Docker로 처리할 부분과 Windows에 남길 부분을 분리하기 위한 운영 기준을 정의한다.
목표는 환경차를 줄이고, 운영 재현성을 높이며, 유지보수 부담을 줄이는 것이다.

## 현재 기준
- `main_webview.py`는 Windows GUI + 로컬 백엔드 통합 진입점이다.
- Docker는 GUI가 없는 백엔드/배치 전용으로 분리한다.
- Windows는 사용자 화면, keyring, WebView2, 로컬 파일, OS 연동을 담당한다.
- Docker는 백엔드 API, 테스트, 정리 작업, 리포트 생성, 백업성 작업을 담당한다.

## 운영 원칙
- GUI는 Windows에서 유지한다.
- keyring, WebView2, 로컬 파일 권한은 Windows 호스트 책임으로 둔다.
- 백엔드, 테스트, 배치성 작업은 Docker로 분리한다.
- Docker는 표준화용, Windows는 실제 실행 환경으로 본다.

## 구분 기준
- 사람이 직접 보는 화면은 Windows에서 처리한다.
- 반복적으로 자동 수행하는 작업은 Docker로 처리한다.
- OS 자격증명 관리자, 파일 탐색기, 트레이 아이콘, 알림창은 Windows 영역으로 본다.
- API 서버, 테스트, 정리 작업, 리포트 생성은 Docker 영역으로 본다.

## 실행 흐름
1. Windows에서 GUI 앱을 시작한다.
2. Docker에서 백엔드 또는 배치 작업을 기동한다.
3. 필요 시 Windows GUI가 Docker 백엔드 주소를 바라보도록 설정한다.
4. keyring 및 환경변수를 확인한다.
5. 로그, 포트, 프로세스 상태를 점검한다.

## 한 줄 요약
Docker는 부품 공장, Windows는 실제 조립 작업대다.
