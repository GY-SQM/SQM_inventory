# SQM Docker / Windows 적용 작업표

## 1단계: 분리 기준 확정
- [ ] GUI는 Windows로 고정
- [ ] keyring은 Windows로 고정
- [ ] WebView2 / pywebview는 Windows로 고정
- [ ] 백엔드 API는 Docker로 분리
- [ ] 테스트는 Docker로 분리
- [ ] cleanup / report / backup 작업은 Docker로 분리

## 2단계: Docker 구성
- [ ] Dockerfile 작성
- [ ] docker-compose.yml 작성
- [ ] .dockerignore 작성
- [ ] 백엔드 전용 진입점 파일 작성
- [ ] 포트 매핑 확인
- [ ] 볼륨 마운트 확인

## 3단계: Windows 구성
- [ ] GUI 실행 절차 확인
- [ ] keyring 저장/조회 확인
- [ ] 로컬 파일 권한 확인
- [ ] 포트 연결 확인
- [ ] 이전 프로세스 종료 확인

## 4단계: 검증
- [ ] py_compile 통과
- [ ] pytest 통과
- [ ] Docker 컨테이너 기동 확인
- [ ] Windows GUI 기동 확인
- [ ] 로그 에러 없음 확인

## 5단계: 운영
- [ ] Windows에서 GUI 실행
- [ ] Docker에서 백엔드 기동
- [ ] 정기 cleanup 작업 실행
- [ ] 정기 report 작업 실행
- [ ] 백업 정리 작업 실행
