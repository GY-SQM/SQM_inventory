# HY Clean Metal v9.0.11 — Patch: mixin import fallback (boot crash fix)

## 발생 문제
- gui/app.py에서 gui.mixins import 실패 시, SealMixin/OcrMixin만 폴백으로 정의되어
  EventMixin 등 다른 mixin이 NameError로 부팅 단계에서 크래시 발생.

## 수정 내용
- gui/app.py의 mixin import 블록을 `except Exception as e:` 로 확장
- import 실패 시 모든 mixin을 object로 폴백 정의하여 NameError 방지
- 실패 원인(repr(e))을 WARN 로그로 출력하여 근본 원인 추적 가능

## 적용 방법
- 본 패치 ZIP을 프로젝트 루트에 덮어쓰기(경로 유지) 후 실행:
  python main.py
