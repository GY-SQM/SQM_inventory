# -*- coding: utf-8 -*-
"""AI 로그 분석 — 반복 오류 패턴 조기 발견."""
import os
import re
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

ERROR_PATTERNS = [
    re.compile(r'(Error|ERROR|Exception|FAIL|Traceback)', re.IGNORECASE),
]


def analyze_logs():
    error_counts = Counter()
    files_checked = 0

    for fname in os.listdir(LOGS_DIR):
        if not fname.endswith('.log'):
            continue
        fpath = os.path.join(LOGS_DIR, fname)
        files_checked += 1
        try:
            with open(fpath, encoding='utf-8', errors='replace') as f:
                for line_no, line in enumerate(f, 1):
                    for pat in ERROR_PATTERNS:
                        if pat.search(line):
                            # Extract error type
                            match = re.search(r'(\w+Error|\w+Exception|FAIL\w*)', line)
                            if match:
                                error_counts[match.group(1)] += 1
                            break
        except Exception:
            pass

    print(f"=== Log Analysis ({files_checked} files) ===")
    if error_counts:
        print("Top error patterns:")
        for err, count in error_counts.most_common(10):
            print(f"  {err}: {count}")
    else:
        print("No error patterns found.")
    return error_counts


if __name__ == '__main__':
    analyze_logs()
