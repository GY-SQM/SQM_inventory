# SQM v5.6.1 전체 소스 + Ultimate Patch 패키지

이 ZIP은 **원본 v5.6.1 전체 소스**와, 한 번에 적용 가능한 **Ultimate Patch**를 함께 담았습니다.

## 구성
- (소스) `engine_modules/`, `gui_app_modular/`, `RUN_APP.py` 등
- (패치) `PATCH/SQM_v561_Ultimate.patch`
- (가이드) `PATCH/README_ULTIMATE_PATCH.md`

## 적용(권장: Git)
소스 폴더로 이동 후:

```bash
git apply --whitespace=nowarn PATCH/SQM_v561_Ultimate.patch
```

## 적용 후
- 톤백 리스트: S0/0, MXBG 제거
- 중량 파싱/단위/샘플무게 기능은 README 가이드에 따라 확인
