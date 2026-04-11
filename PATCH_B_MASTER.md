# PATCH_B_MASTER.md
작성일: 2026-04-07
인코딩: UTF-8

## 목적
outbound_mixin.py를 Query / Repository / Service / State Rules 구조로 분해하고,
scan → SOLD 정책을 안전하게 보존한다.

## Step 구성
- B01: outbound_mixin 흐름 분석
- B02: Query 분리
- B03: State Rules 문서화
- B04: Write Repository 분리
- B05: Service 도입
- B06: Transaction boundary 정리
- B07: 테스트 수행
- B08: 검증 및 최종 정리

## 핵심 원칙
- mixin은 UI adapter만 남긴다
- SELECT는 query repo
- UPDATE/INSERT는 write repo
- scan → SOLD는 service에서만 결정
- transaction은 한 블록으로 묶는다
