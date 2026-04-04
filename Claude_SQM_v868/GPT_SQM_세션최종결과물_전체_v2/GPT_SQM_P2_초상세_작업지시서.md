# GPT_SQM_P2_초상세_작업지시서.md
생성일: 2026-04-04 17:08 (Asia/Seoul)

[질문] P2 단계 초상세 작업지시서 작성
[질문의도] React UI를 Tkinter 수준 이상으로 끌어올리기 위한 구체 실행 지침 제공

# [응답]

## 1. 목표
- Tkinter UI 기능 90% 이상 React에서 재현
- 주요 화면 (Return/Move/Scan/Log) 복구
- UX 개선 (모달, 필터, 상태표시)

## 2. 작업 범위
- web/src/pages/*
- web/src/components/*
- react_api/routes/*
- react_api/services/*

## 3. 핵심 작업

### 3-1 LOT 상세 강화
- 상태 표시 (AVAILABLE/RESERVED/SOLD)
- TONBAG 리스트 표시

### 3-2 메뉴 확장
- Return 화면
- Move 화면
- Scan 화면

### 3-3 UX 개선
- 로딩 상태 표시
- 에러 메시지 통일
- 필터/검색 UX 개선

## 4. 금지
- engine_modules 수정 금지
- mock 데이터 금지

## 5. 완료 기준
- 주요 화면 정상 동작
- API 연동 성공
- 사용자 흐름 막힘 없음
