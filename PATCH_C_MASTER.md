# PATCH_C_MASTER.md
작성일: 2026-04-07
인코딩: UTF-8

## 목적
Repository Pattern을 도입하여 DB 접근 방식을 전체적으로 통일한다.

## Step 구성
- C01: DB 접근 전수조사
- C02: BaseRepository 도입
- C03: Inventory repository 적용
- C04: Inbound repository 적용
- C05: Outbound repository 적용
- C06: commit/rollback/예외 정책 통일

## 핵심 원칙
- business rule은 변경하지 않는다
- DB 접근만 정리한다
- commit/rollback 정책을 BaseRepository 기준으로 통일한다
