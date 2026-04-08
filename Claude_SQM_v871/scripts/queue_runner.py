# -*- coding: utf-8 -*-
"""작업 큐 관리 — completed_steps.txt 기반 다음 단계 안내."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEPS_FILE = os.path.join(BASE_DIR, 'logs', 'completed_steps.txt')

ALL_STEPS = [
    "P0-S1","P0-S2","P0-S3","P0-S4","P0-S5","P0-S6","P0-S7","P0-S8",
    "P0-S9","P0-S10","P0-S11","P0-S12","P0-S13","P0-S14","P0-S15",
    "P1-S1","P1-S2","P1-S3","P1-S4","P1-S5","P1-S6","P1-S7","P1-S8",
    "P1-S9","P1-S10","P1-S11","P1-S12",
    "P2-S1","P2-S2","P2-S3","P2-S4","P2-S5","P2-S6",
    "P3-S1","P3-S2","P3-S3","P3-S4","P3-S5","P3-S6","P3-S7",
    "P4-S1","P4-S2","P4-S3","P4-S4","P4-S5","P4-S6","P4-S7","P4-S8","P4-S9",
]


def get_completed():
    done = set()
    if os.path.exists(STEPS_FILE):
        with open(STEPS_FILE, encoding='utf-8', errors='replace') as f:
            for line in f:
                for step in ALL_STEPS:
                    if line.strip().startswith(step + '_') and '_PASS' in line:
                        done.add(step)
    return done


def next_step():
    done = get_completed()
    for s in ALL_STEPS:
        if s not in done:
            return s
    return None


if __name__ == '__main__':
    done = get_completed()
    nxt = next_step()
    print(f"Completed: {len(done)}/{len(ALL_STEPS)}")
    if nxt:
        print(f"Next: {nxt}")
    else:
        print("All steps completed!")
