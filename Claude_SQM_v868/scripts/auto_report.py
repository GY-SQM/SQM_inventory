# -*- coding: utf-8 -*-
"""자동 보고서 생성 — completed_steps.txt 기반."""
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
STEPS_FILE = os.path.join(LOGS_DIR, 'completed_steps.txt')

TOTAL_STEPS = 49


def parse_completed():
    completed = []
    if os.path.exists(STEPS_FILE):
        with open(STEPS_FILE, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if line and '_PASS' in line:
                    completed.append(line)
    return completed


def generate_report():
    completed = parse_completed()
    pct = round(len(completed) / TOTAL_STEPS * 100) if TOTAL_STEPS else 0
    bar = '█' * (pct // 5) + '░' * (20 - pct // 5)

    lines = [
        f"# SQM v868 Auto Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## Progress: {len(completed)}/{TOTAL_STEPS} ({pct}%)",
        f"[{bar}]",
        f"",
        f"## Completed Steps",
    ]
    for step in completed:
        lines.append(f"- {step}")

    report_path = os.path.join(LOGS_DIR, 'auto_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"Report saved: {report_path}")
    return report_path


if __name__ == '__main__':
    generate_report()
