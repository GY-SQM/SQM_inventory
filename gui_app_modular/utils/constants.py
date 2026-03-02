"""
GUI 상수 re-export (P2: 단일 소스는 gui_bootstrap)
"""
from .gui_bootstrap import *  # noqa: F401, F403

# import * 는 __로 시작하는 이름을 내보내지 않으므로 명시 re-export
from .gui_bootstrap import APP_NAME, __version__  # noqa: F401
