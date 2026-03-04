SQM PREMIUM UI v7 (Prototype) - Ruby

실행 방법
1) 설치
   pip install ttkbootstrap

2) 실행
   python SQM_PREMIUM_UI_v7.py

특징(루비안)
- 다크/라이트 토글(기본은 다크)
- 고급 다크 팔레트(배경/패널/카드 3단 명도 + 절제된 포인트)
- 메인 테이블(Treeview) 가독성 중심(선택색 절제)
- 상태(available/reserved/picked/shipped) 행 색은 "부드럽게" 적용

SQM 실프로젝트에 이식할 때(권장)
- 테마 적용은 1곳에서만(ReadableStyle.apply 또는 전역 ThemeMixin) 유지
- Treeview 상태색은 tag_configure + insert(tags=(status,))
- odd/even 줄무늬는 status가 있는 행에는 배경을 덮지 않게(안전 스트라이프)
