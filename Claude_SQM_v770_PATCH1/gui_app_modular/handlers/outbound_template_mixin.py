# -*- coding: utf-8 -*-
"""
SQM v4.0.1 — 출고 템플릿/Allocation Mixin
===========================================

outbound_handlers.py에서 분리:
- 출고 양식 다운로드
- Allocation Table 생성 (샘플)
- Virtual Allocation 생성
"""
import logging
from ..utils.custom_messagebox import CustomMessageBox

logger = logging.getLogger(__name__)


class OutboundTemplateMixin:
    """출고 템플릿 및 Allocation Table Mixin"""


    def _generate_allocation_samples(self) -> None:
        """화주 양식(PT LBM / CN Semarang) Allocation 샘플 Excel 3개 생성"""
        import subprocess
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        script_path = project_root / "scripts" / "generate_allocation_from_tonbag.py"
        out_dir = project_root / "generated_allocation"

        if not script_path.exists():
            CustomMessageBox.showerror(self.root, "오류", f"스크립트 없음: {script_path}")
            return

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
            out = (result.stdout or '') + (result.stderr or '')
            if result.returncode == 0:
                self._log("✅ Allocation 샘플 3개 생성 완료")
                CustomMessageBox.showinfo(
                    self.root, "완료",
                    f"Allocation Table 샘플 3개 생성 완료\n\n"
                    f"출력 폴더:\n{out_dir}\n\n"
                    f"파일: Allocation_샘플_1.xlsx, 2.xlsx, 3.xlsx"
                )
            else:
                logger.warning(f"Allocation 샘플 생성 비정상 종료: {result.returncode}\n{out}")
                CustomMessageBox.showwarning(
                    self.root, "경고",
                    f"생성 중 오류 발생 (코드 {result.returncode})\n\n{out[:500]}"
                )
        except subprocess.TimeoutExpired:
            CustomMessageBox.showerror(self.root, "오류", "생성 시간 초과(60초)")
        except Exception as e:
            logger.error(f"Allocation 샘플 생성 오류: {e}", exc_info=True)
            CustomMessageBox.show_detailed_error(self.root, "오류", "Allocation 샘플 생성 실패", exception=e)

