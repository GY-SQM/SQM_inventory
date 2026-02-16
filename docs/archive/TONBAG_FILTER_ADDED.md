# 톤백 리스트 필터 추가 완료

**버전**: v5.0.2  
**날짜**: 2026-02-11

---

## ✅ 추가된 기능

### 톤백 리스트 필터바
재고 리스트와 동일한 필터바를 톤백 리스트에도 추가했습니다!

**필터 항목 (6개)**:
1. ✅ LOT NO
2. ✅ SAP NO
3. ✅ BL NO
4. ✅ CONTAINER
5. ✅ PRODUCT
6. ✅ STATUS

**기존 필터 유지**:
- ✅ 상태 필터 (전체/AVAILABLE/SOLD/PICKED/SAMPLE)
- ✅ 샘플 표시/숨김 체크박스
- ✅ 검색창

---

## 📝 수정된 파일

```
gui_app_modular/tabs/tonbag_tab.py
├─ _setup_tonbag_tab()           ← HeaderFilterBar 추가
├─ _on_tonbag_filter_apply()     ← 필터 적용 함수 (신규)
└─ _refresh_tonbag()              ← 필터 조건 적용
```

---

## 🎯 사용 방법

### 1. 필터 펼치기
```
톤백 리스트 탭 상단
→ "▼ 필터" 클릭
```

### 2. 필터 선택
```
LOT NO: [전체 ▼]
SAP NO: [전체 ▼]
BL NO: [전체 ▼]
...
```

### 3. 컬럼 표시/숨김
```
☑ SAP NO
☑ BL NO
☑ CONTAINER
...
```

---

## 🧪 테스트

- [ ] 톤백 리스트 탭 열기
- [ ] 상단에 필터바 표시
- [ ] LOT NO 필터 작동
- [ ] SAP NO 필터 작동
- [ ] 컬럼 표시/숨김 작동
- [ ] 기존 상태 필터 정상 작동
- [ ] 검색창 정상 작동

---

**Ruby's Note**:  
"이제 톤백 리스트도 재고 리스트처럼 강력한 필터 기능을 사용할 수 있어요!" 🎯✨
