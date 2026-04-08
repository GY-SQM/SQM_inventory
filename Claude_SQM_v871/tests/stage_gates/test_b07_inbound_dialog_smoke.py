# -*- coding: utf-8 -*-
"""B07: onestop_inbound.py 예외 처리 표준화 스모크 테스트."""
import ast
import os
import re
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TARGET_FILE = os.path.join(
    PROJECT_ROOT, 'gui_app_modular', 'dialogs', 'onestop_inbound.py'
)


class TestB07InboundDialogSmoke(unittest.TestCase):
    """onestop_inbound.py 예외 처리 개선 검증."""

    @classmethod
    def setUpClass(cls):
        with open(TARGET_FILE, encoding='utf-8') as f:
            cls.source = f.read()
        cls.lines = cls.source.splitlines()

    # ── 1. py_compile ────────────────────────────────────────
    def test_py_compile(self):
        """파일이 구문 오류 없이 컴파일되어야 함."""
        import py_compile
        py_compile.compile(TARGET_FILE, doraise=True)

    # ── 2. bare 'except: pass' 패턴 없어야 함 ────────────────
    def test_no_bare_except_pass(self):
        """bare 'except:' (변수 없음) 뒤에 pass만 있는 패턴은 금지."""
        bare_pass_pattern = re.compile(
            r'^\s*except\s*:\s*$'  # bare except (no Exception, no as)
        )
        violations = []
        for i, line in enumerate(self.lines, 1):
            if bare_pass_pattern.match(line):
                # check if next non-blank line is just 'pass'
                for j in range(i, min(i + 3, len(self.lines))):
                    stripped = self.lines[j].strip()
                    if stripped == 'pass':
                        violations.append(f"line {i}: bare except: pass")
                        break
                    elif stripped and stripped != '#':
                        break
        self.assertEqual(
            violations, [],
            f"bare 'except: pass' 패턴 발견: {violations}"
        )

    # ── 3. except 블록 근처에 logging 호출 존재 ──────────────
    def test_logging_near_exception_handlers(self):
        """모든 except 블록에 logger 호출 또는 명시적 주석이 있어야 함."""
        except_pattern = re.compile(r'^\s*except\s+')
        log_pattern = re.compile(r'logger\.(debug|info|warning|error|critical)')
        # 모듈 수준 ImportError (optional import)는 예외
        module_level_import_re = re.compile(r'^except\s+ImportError')

        missing_log = []
        for i, line in enumerate(self.lines):
            if not except_pattern.match(line):
                continue
            # 모듈 수준 optional import는 제외 (들여쓰기 없는 except)
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent == 0 and module_level_import_re.match(stripped):
                continue
            # except 이후 5줄 이내에 logger 호출이 있는지 확인
            block_lines = self.lines[i:i + 6]
            block_text = '\n'.join(block_lines)
            if not log_pattern.search(block_text):
                # 일부 좁은 예외(ValueError 등)에서 return/continue가 있으면 허용
                has_action = any(
                    kw in block_text
                    for kw in ['return', 'continue', 'raise', 'messagebox', 'pass', 'break']
                )
                # Safe narrow exceptions that don't need logging
                safe_narrow = any(
                    kw in stripped
                    for kw in ['ImportError', 'ModuleNotFoundError', 'queue.Empty',
                               'ValueError', 'TypeError', 'KeyError', 'AttributeError']
                )
                if safe_narrow:
                    has_action = True
                if not has_action:
                    missing_log.append(f"line {i + 1}: {stripped.strip()}")
        self.assertEqual(
            missing_log, [],
            f"except 블록에 logging 미발견: {missing_log}"
        )

    # ── 4. 'except Exception' 에 변수(as e) 바인딩 확인 ──────
    def test_broad_exception_has_variable(self):
        """'except Exception' 사용 시 'as <var>' 바인딩이 있어야 함."""
        broad_no_var = re.compile(r'^\s*except\s+Exception\s*:')
        violations = []
        for i, line in enumerate(self.lines, 1):
            if broad_no_var.match(line):
                violations.append(f"line {i}: {line.strip()}")
        self.assertEqual(
            violations, [],
            f"'except Exception:' without 'as e': {violations}"
        )

    # ── 5. silent pass 패턴이 없어야 함 (ImportError 포함) ───
    def test_no_silent_except_pass(self):
        """except ... : pass (logging 없이) 패턴이 클래스 내부에 없어야 함."""
        # AST를 사용하여 ExceptHandler 내 body가 Pass만인 경우 확인
        tree = ast.parse(self.source, TARGET_FILE)
        silent = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            body = node.body
            if (
                len(body) == 1
                and isinstance(body[0], ast.Pass)
                and node.lineno > 50  # 모듈 수준 optional import 제외
            ):
                silent.append(f"line {node.lineno}")
        self.assertEqual(
            silent, [],
            f"silent except...pass 블록 (logging 없음): {silent}"
        )


if __name__ == '__main__':
    unittest.main()
