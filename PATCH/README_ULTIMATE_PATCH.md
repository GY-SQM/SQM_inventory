# SQM v5.6.1 Ultimate Patch 적용 안내

## 포함
- `SQM_v561_Ultimate.patch` : 통합 패치(아래 2개를 한 파일로 합친 것)
  - (A) S0 표시 + 샘플 순번 0 + MXBG 컬럼 제거 (톤백 리스트 UI/Export)
  - (B) 중량 파싱(5.001 -> 5,001kg 등) + 단위 kg/MT 선택 + BL 공통 샘플 무게 설정(기본 1kg)

## 적용(권장: Git)
프로젝트 루트에서:

```bash
git status
# 작업 파일이 있으면 커밋/스태시 후 진행 권장

git apply --whitespace=nowarn SQM_v561_Ultimate.patch
```

## (대안) patch 명령
```bash
patch -p0 < SQM_v561_Ultimate.patch
```

## 적용 후 바로 확인(체크리스트)
1) 톤백 리스트
- 샘플 행: No=0, TONBAG NO=S0
- MXBG 컬럼이 보이지 않음
- Export에도 MXBG 컬럼 없음

2) 중량 파싱/단위
- 5.001 입력/문서값이 5,001kg로 내부 계산되는지 확인
- 단위 선택: 기본 kg, 필요 시 MT 선택 가능(선택 즉시 재계산)

3) 샘플 무게
- BL 공통 샘플 무게 기본값 1.0kg
- 사용자가 변경 가능(변경 시 정합성 재검증)

## 주의
- 이 패치는 v5.6.1 코드 베이스 기준입니다. 파일 경로/구조가 크게 다르면 충돌이 날 수 있습니다.
