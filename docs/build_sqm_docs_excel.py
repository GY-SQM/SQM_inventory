#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs/ 내 CSV 4개를 하나의 엑셀 파일로 합칩니다.
시트: 매트릭스_공통헤더, 매트릭스_단일헤더, 변수_DB컬럼, 변수_상수

실행: 프로젝트 루트에서
  python docs/build_sqm_docs_excel.py
또는 docs 폴더에서
  python build_sqm_docs_excel.py
"""
import csv
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("pandas가 필요합니다: pip install pandas openpyxl")
    raise

DOCS = Path(__file__).resolve().parent
OUTPUT = DOCS / "SQM_변수_테이블_문서.xlsx"

CSV_SHEETS = [
    ("SQM_테이블_헤더_매트릭스_공통헤더.csv", "매트릭스_공통헤더"),
    ("SQM_테이블_헤더_매트릭스_단일헤더.csv", "매트릭스_단일헤더"),
    ("SQM_변수_컬럼_목록_DB컬럼.csv", "변수_DB컬럼"),
    ("SQM_변수_컬럼_목록_상수.csv", "변수_상수"),
]


def read_csv_safe(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    """CSV를 읽되, 열 수가 맞지 않는 행은 헤더 열 수에 맞춰 잘라서 DataFrame 반환."""
    with open(path, "r", encoding=encoding) as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return pd.DataFrame()
    header = rows[0]
    ncol = len(header)
    data = []
    for r in rows[1:]:
        if len(r) > ncol:
            r = r[:ncol]
        elif len(r) < ncol:
            r = r + [""] * (ncol - len(r))
        data.append(r)
    return pd.DataFrame(data, columns=header)


def main():
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        # 목차 시트: 파일 위치 + 요청하신 데이터가 모두 들어있음 안내
        toc = pd.DataFrame([
            ["SQM 변수·테이블 문서 — 목차", ""],
            ["", ""],
            ["■ 파일 위치", ""],
            ["  이 엑셀 파일", "docs/SQM_변수_테이블_문서.xlsx (프로젝트 루트 기준 docs 폴더)"],
            ["  전체 경로 예", "d:\\프로그램\\Sqm\\SQM_v590\\docs\\SQM_변수_테이블_문서.xlsx"],
            ["", ""],
            ["■ 시트 구성 (요청하신 데이터 모두 포함)", ""],
            ["시트 이름", "내용"],
            ["매트릭스_공통헤더", "13개 테이블 × 공통 헤더 31개 (O=해당 테이블에 컬럼 있음). 열 순서=헤더 사용 테이블 수 많은 순"],
            ["매트릭스_단일헤더", "13개 테이블 × 1개 테이블 전용 헤더 (O 표시)"],
            ["변수_DB컬럼", "DB 컬럼: 변수명, 의미, 타입, 사용처(테이블) — 프로그램에 나온 DB 데이터 헤더 전부"],
            ["변수_상수", "비즈니스 상수: 변수명, 의미, 타입, 사용처 — engine_modules.constants / core.constants"],
            ["", ""],
            ["■ 요청 사항 대비", ""],
            ["1. 모든 변수 이름·의미·타입·어디에 쓰이는지", "→ 변수_DB컬럼 + 변수_상수 시트에 모두 포함"],
            ["2. 모든 테이블(행) × 데이터 헤더(열), 열 순서=헤더 많이 쓰인 순", "→ 매트릭스_공통헤더 + 매트릭스_단일헤더 시트에 모두 포함"],
        ])
        toc.to_excel(writer, sheet_name="목차", index=False, header=False)
        print("  시트 추가: 목차")

        for csv_name, sheet_name in CSV_SHEETS:
            path = DOCS / csv_name
            if not path.exists():
                print(f"  [건너뜀] 없음: {path}")
                continue
            df = read_csv_safe(path)
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"  시트 추가: {sheet_name} ({len(df)}행)")
    print(f"\n저장: {OUTPUT}")


if __name__ == "__main__":
    main()
