# AGENT_TEAM_MASTER.md
작성일: 2026-04-07
인코딩: UTF-8

## Agent Team 구조
1. Architect Agent
2. Refactor Agent (Claude Code)
3. Verification Agent
4. Debug Agent
5. UI / React Agent

## 실행 흐름
Architect → Refactor → Verification → Debug → PASS 시 다음 단계

## 공통 원칙
- 한 번에 하나의 Step만
- FAIL이면 다음 단계 금지
- 모든 로그는 logs/
- 모든 문서는 UTF-8
