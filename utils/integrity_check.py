"""
SQM 재고관리 시스템 - 데이터 정합성 검사 리포트 (v3.8.4)
=======================================================

DB 이관 전/운영 중 데이터 무결성을 자동 점검합니다.

검사 항목:
    1. 중복 LOT 번호
    2. 고아 TONBAG (LOT에 연결 안 됨)
    3. 날짜 포맷 불량 (ISO 8601 위반)
    4. 수량/중량 불일치 (음수, 비정상 0)
    5. FK 위반 (외래키 무결성)
    6. 상태 불일치 (AVAILABLE인데 중량 0 등)

사용법:
    >>> from utils.integrity_check import IntegrityChecker
    >>> checker = IntegrityChecker(db)
    >>> report = checker.run_all()
    >>> checker.print_report(report)

Author: Ruby
Version: v3.8.4
"""

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


# ISO 8601 날짜 패턴 (YYYY-MM-DD)
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}')


@dataclass
class CheckResult:
    """개별 검사 결과"""
    check_name: str
    passed: bool
    issue_count: int = 0
    details: List[str] = field(default_factory=list)
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL


@dataclass
class IntegrityReport:
    """전체 정합성 리포트"""
    timestamp: str = ""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    results: List[CheckResult] = field(default_factory=list)

    @property
    def score(self) -> int:
        """정합성 점수 (0~100)"""
        if self.total_checks == 0:
            return 100
        return int((self.passed / self.total_checks) * 100)


class IntegrityChecker:
    """데이터 정합성 검사기"""

    def __init__(self, db):
        """
        Args:
            db: SQMDatabase 인스턴스
        """
        self.db = db

    def run_all(self) -> IntegrityReport:
        """전체 정합성 검사 실행"""
        report = IntegrityReport(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        checks = [
            self._check_duplicate_lots,
            self._check_orphan_tonbags,
            self._check_date_formats,
            self._check_weight_integrity,
            self._check_status_consistency,
            self._check_fk_integrity,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
                report.results.append(result)
                report.total_checks += 1
                if result.passed:
                    report.passed += 1
                elif result.severity == "WARNING":
                    report.warnings += 1
                else:
                    report.failed += 1
            except (AttributeError, RuntimeError) as e:
                logger.error(f"정합성 검사 오류 ({check_fn.__name__}): {e}")
                report.results.append(CheckResult(
                    check_name=check_fn.__name__,
                    passed=False,
                    issue_count=1,
                    details=[f"검사 실행 오류: {e}"],
                    severity="ERROR"
                ))
                report.total_checks += 1
                report.failed += 1

        return report

    def _check_duplicate_lots(self) -> CheckResult:
        """1. 중복 LOT 번호 검사"""
        rows = self.db.fetchall("""
            SELECT lot_no, COUNT(*) as cnt 
            FROM inventory 
            WHERE lot_no IS NOT NULL AND lot_no != ''
            GROUP BY lot_no 
            HAVING cnt > 1
        """)

        issues = []
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            cnt = row['cnt'] if isinstance(row, dict) else row[1]
            issues.append(f"LOT '{lot_no}' → {cnt}건 중복")

        return CheckResult(
            check_name="중복 LOT 번호",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],  # 최대 20건
            severity="CRITICAL" if issues else "INFO"
        )

    def _check_orphan_tonbags(self) -> CheckResult:
        """2. 고아 TONBAG 검사 (LOT에 연결 안 됨)"""
        rows = self.db.fetchall("""
            SELECT t.id, t.lot_no, t.sub_lt
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE i.id IS NULL AND t.lot_no IS NOT NULL AND t.lot_no != ''
        """)

        issues = []
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[1]
            sub_lt = row['sub_lt'] if isinstance(row, dict) else row[2]
            issues.append(f"TONBAG {lot_no}-{sub_lt} → inventory에 LOT 없음")

        return CheckResult(
            check_name="고아 TONBAG (LOT 미연결)",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],
            severity="ERROR" if issues else "INFO"
        )

    def _check_date_formats(self) -> CheckResult:
        """3. 날짜 포맷 불량 검사 (ISO 8601 위반)"""
        date_columns = [
            ("inventory", "ship_date"),
            ("inventory", "arrival_date"),
            ("inventory", "inbound_date"),
            ("inventory", "stock_date"),
            ("inventory_tonbag", "inbound_date"),
        ]

        issues = []
        for table, column in date_columns:
            try:
                rows = self.db.fetchall(f"""
                    SELECT id, {column} 
                    FROM {table} 
                    WHERE {column} IS NOT NULL 
                      AND {column} != '' 
                      AND {column} NOT LIKE '____-__-__%%'
                """)
                for row in rows:
                    row_id = row['id'] if isinstance(row, dict) else row[0]
                    val = row[column] if isinstance(row, dict) else row[1]
                    issues.append(f"{table}.{column} (id={row_id}): '{val}'")
            except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                logger.debug(f"[integrity_check] 무시: {_e}")

        return CheckResult(
            check_name="날짜 포맷 불량 (ISO 8601)",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],
            severity="WARNING" if issues else "INFO"
        )

    def _check_weight_integrity(self) -> CheckResult:
        """4. 수량/중량 불일치 검사"""
        issues = []

        # 음수 중량
        rows = self.db.fetchall("""
            SELECT lot_no, net_weight, current_weight, picked_weight
            FROM inventory
            WHERE net_weight < 0 OR current_weight < 0 OR picked_weight < 0
        """)
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            issues.append(f"LOT '{lot_no}' → 음수 중량 발견")

        # current_weight > initial_weight (비정상)
        rows = self.db.fetchall("""
            SELECT lot_no, initial_weight, current_weight
            FROM inventory
            WHERE initial_weight > 0 AND current_weight > initial_weight
        """)
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            initial = row['initial_weight'] if isinstance(row, dict) else row[1]
            current = row['current_weight'] if isinstance(row, dict) else row[2]
            issues.append(f"LOT '{lot_no}' → current({current}) > initial({initial})")

        # TONBAG 음수 중량
        rows = self.db.fetchall("""
            SELECT lot_no, sub_lt, weight
            FROM inventory_tonbag
            WHERE weight < 0
        """)
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            sub_lt = row['sub_lt'] if isinstance(row, dict) else row[1]
            issues.append(f"TONBAG {lot_no}-{sub_lt} → 음수 중량")

        return CheckResult(
            check_name="수량/중량 불일치",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],
            severity="ERROR" if issues else "INFO"
        )

    def _check_status_consistency(self) -> CheckResult:
        """5. 상태 불일치 검사"""
        issues = []

        # AVAILABLE인데 current_weight = 0
        rows = self.db.fetchall("""
            SELECT lot_no, status, current_weight
            FROM inventory
            WHERE status = 'AVAILABLE' AND current_weight <= 0
              AND initial_weight > 0
        """)
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            issues.append(f"LOT '{lot_no}' → AVAILABLE인데 잔량 0 (DEPLETED여야 함)")

        # DEPLETED인데 current_weight > 0
        rows = self.db.fetchall("""
            SELECT lot_no, status, current_weight
            FROM inventory
            WHERE status = 'DEPLETED' AND current_weight > 0
        """)
        for row in rows:
            lot_no = row['lot_no'] if isinstance(row, dict) else row[0]
            current = row['current_weight'] if isinstance(row, dict) else row[2]
            issues.append(f"LOT '{lot_no}' → DEPLETED인데 잔량 {current}kg")

        return CheckResult(
            check_name="상태 불일치 (STATUS vs 중량)",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],
            severity="WARNING" if issues else "INFO"
        )

    def _check_fk_integrity(self) -> CheckResult:
        """6. FK 무결성 검사"""
        issues = []

        # inventory.shipment_id → shipment.id
        try:
            rows = self.db.fetchall("""
                SELECT i.id, i.lot_no, i.shipment_id
                FROM inventory i
                LEFT JOIN shipment s ON i.shipment_id = s.id
                WHERE i.shipment_id IS NOT NULL AND s.id IS NULL
            """)
            for row in rows:
                lot_no = row['lot_no'] if isinstance(row, dict) else row[1]
                sid = row['shipment_id'] if isinstance(row, dict) else row[2]
                issues.append(f"LOT '{lot_no}' → shipment_id={sid} 존재하지 않음")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
            logger.warning(f"Suppressed: {_e}")

        # inventory_tonbag.inventory_id → inventory.id
        try:
            rows = self.db.fetchall("""
                SELECT t.id, t.lot_no, t.inventory_id
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.inventory_id = i.id
                WHERE t.inventory_id IS NOT NULL AND i.id IS NULL
            """)
            for row in rows:
                lot_no = row['lot_no'] if isinstance(row, dict) else row[1]
                iid = row['inventory_id'] if isinstance(row, dict) else row[2]
                issues.append(f"TONBAG {lot_no} → inventory_id={iid} 존재하지 않음")
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
            logger.warning(f"Suppressed: {_e}")

        return CheckResult(
            check_name="FK 무결성 (외래키 참조)",
            passed=len(issues) == 0,
            issue_count=len(issues),
            details=issues[:20],
            severity="ERROR" if issues else "INFO"
        )

    def print_report(self, report: IntegrityReport) -> str:
        """리포트를 텍스트로 출력"""
        lines = []
        lines.append("=" * 60)
        lines.append("  SQM 데이터 정합성 리포트 (v3.8.7)")
        lines.append(f"  검사 시각: {report.timestamp}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  총 검사: {report.total_checks}건")
        lines.append(f"  ✅ 통과: {report.passed}건")
        lines.append(f"  ⚠️ 경고: {report.warnings}건")
        lines.append(f"  ❌ 실패: {report.failed}건")
        lines.append(f"  📊 점수: {report.score}/100")
        lines.append("")
        lines.append("-" * 60)

        for r in report.results:
            icon = "✅" if r.passed else ("⚠️" if r.severity == "WARNING" else "❌")
            lines.append(f"  {icon} {r.check_name}: {r.issue_count}건")
            if r.details:
                for d in r.details[:5]:
                    lines.append(f"      → {d}")
                if len(r.details) > 5:
                    lines.append(f"      ... 외 {len(r.details) - 5}건")

        lines.append("")
        lines.append("=" * 60)

        text = "\n".join(lines)
        logger.info(f"정합성 리포트 생성 완료 (점수: {report.score}/100)")
        return text

    def save_report(self, report: IntegrityReport, filepath: str = None) -> str:
        """리포트를 파일로 저장"""
        import os

        if filepath is None:
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'REPORTS')
            os.makedirs(reports_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = os.path.join(reports_dir, f'INTEGRITY_{timestamp}.txt')

        text = self.print_report(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)

        logger.info(f"정합성 리포트 저장: {filepath}")
        return filepath


# 편의 함수
def run_integrity_check(db) -> IntegrityReport:
    """정합성 검사 실행 (간편 호출)"""
    checker = IntegrityChecker(db)
    return checker.run_all()
