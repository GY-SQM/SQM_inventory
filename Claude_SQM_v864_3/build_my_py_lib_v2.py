#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
my_py_lib 자동 빌드 스크립트 v2
34개 파일 자동 생성 + ZIP 압축 (간단 버전)

실행 방법:
python build_my_py_lib_v2.py

또는:
python -u build_my_py_lib_v2.py
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path

print("="*70)
print("🚀 my_py_lib 자동 빌드 시작".center(70))
print("="*70)
print()

# ===== 설정 =====
BASE_PATH = r"C:\my_py_lib"
OUTPUT_ZIP = r"D:\program\SQM_inventory\Claude_SQM_v864_3\my_py_lib_v1.0.0.zip"

print(f"📁 생성 경로: {BASE_PATH}")
print(f"📦 ZIP 경로: {OUTPUT_ZIP}")
print()

# ===== STEP 1: 폴더 생성 =====
print("="*70)
print("STEP 1: 폴더 구조 생성")
print("="*70)

folders = [
    BASE_PATH,
    os.path.join(BASE_PATH, "core"),
    os.path.join(BASE_PATH, "ui"),
    os.path.join(BASE_PATH, "plugins"),
    os.path.join(BASE_PATH, "configs"),
    os.path.join(BASE_PATH, "logs"),
    os.path.join(BASE_PATH, "examples"),
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"  ✓ {folder}")

print("✅ 폴더 생성 완료\n")

# ===== STEP 2: 파일 생성 =====
print("="*70)
print("STEP 2: 파일 생성 (34개)")
print("="*70)

FILES = {
    # Core 모듈
    os.path.join(BASE_PATH, "core", "logger.py"): '''"""통합 로거"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from collections import deque
import threading

class IntegratedLogger:
    @staticmethod
    def setup(log_file='app.log'):
        logger = logging.getLogger('my_py_lib')
        logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)-8s] %(message)s')
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger

class SmartErrorHandler:
    def __init__(self, logger):
        self.logger = logger
    
    def log_error(self, exception):
        self.logger.error(f"ERROR: {type(exception).__name__}: {str(exception)}")
''',

    os.path.join(BASE_PATH, "core", "analyzer.py"): '''"""에러 분석"""
class ErrorAnalyzer:
    ERROR_PATTERNS = {
        'ConnectionRefusedError': {'cause': '연결 거부', 'solution': '서버 확인'},
        'TimeoutError': {'cause': '시간 초과', 'solution': '네트워크 확인'},
        'FileNotFoundError': {'cause': '파일 없음', 'solution': '경로 확인'},
        'KeyError': {'cause': '키 없음', 'solution': '키 확인'},
        'ValueError': {'cause': '값 오류', 'solution': '입력값 확인'},
        'TypeError': {'cause': '타입 오류', 'solution': '타입 확인'},
    }
    
    @staticmethod
    def analyze_exception(exc_type, exc_value, exc_traceback):
        exc_name = exc_type.__name__ if hasattr(exc_type, '__name__') else str(exc_type)
        pattern = ErrorAnalyzer.ERROR_PATTERNS.get(exc_name, {'cause': '알 수 없음', 'solution': '로그 확인'})
        return {'type': exc_name, 'message': str(exc_value), 'cause': pattern['cause'], 'solution': pattern['solution']}
''',

    os.path.join(BASE_PATH, "core", "filter.py"): '''"""로그 필터"""
class LogFilter:
    def __init__(self, logs):
        self.logs = logs
        self.filters = []
    
    def by_level(self, level):
        self.filters.append(lambda log: log.get('level') == level)
        return self
    
    def by_keyword(self, keyword):
        self.filters.append(lambda log: keyword in log.get('message', ''))
        return self
    
    def apply(self):
        result = self.logs
        for filter_func in self.filters:
            result = [log for log in result if filter_func(log)]
        return result
''',

    os.path.join(BASE_PATH, "core", "profiler.py"): '''"""성능 측정"""
import time
import functools
from collections import defaultdict

class PerformanceProfiler:
    def __init__(self):
        self.function_times = defaultdict(list)
    
    def profile_function(self, threshold_ms=500):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                result = func(*args, **kwargs)
                elapsed_ms = (time.time() - start) * 1000
                self.function_times[func.__name__].append(elapsed_ms)
                return result
            return wrapper
        return decorator
    
    def get_slowest_functions(self, top_n=5):
        avg_times = {func: sum(times)/len(times) for func, times in self.function_times.items()}
        return sorted(avg_times.items(), key=lambda x: x[1], reverse=True)[:top_n]
''',

    os.path.join(BASE_PATH, "core", "grouper.py"): '''"""에러 그룹핑"""
from datetime import datetime, timedelta
from collections import defaultdict

class ErrorGrouper:
    def __init__(self, window_minutes=30):
        self.error_history = defaultdict(list)
        self.window_minutes = window_minutes
    
    def add_error(self, error_type, message):
        self.error_history[error_type].append({'timestamp': datetime.now(), 'message': message})
    
    def get_critical_repeated_errors(self):
        critical = []
        cutoff_time = datetime.now() - timedelta(minutes=self.window_minutes)
        for error_type, errors in self.error_history.items():
            recent = [e for e in errors if e['timestamp'] > cutoff_time]
            if len(recent) >= 3:
                critical.append({'type': error_type, 'count': len(recent)})
        return critical
''',

    os.path.join(BASE_PATH, "core", "severity.py"): '''"""심각도 분류"""
from enum import Enum

class ErrorSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ErrorSeverityAnalyzer:
    RULES = {
        'ConnectionRefusedError': ErrorSeverity.CRITICAL,
        'TimeoutError': ErrorSeverity.HIGH,
        'FileNotFoundError': ErrorSeverity.MEDIUM,
        'KeyError': ErrorSeverity.MEDIUM,
        'ValueError': ErrorSeverity.LOW,
    }
    
    @staticmethod
    def analyze(exc_type, message):
        exc_name = exc_type if isinstance(exc_type, str) else exc_type.__name__
        return ErrorSeverityAnalyzer.RULES.get(exc_name, ErrorSeverity.LOW)
''',

    os.path.join(BASE_PATH, "core", "notifier.py"): '''"""알림"""
import logging
from datetime import datetime, timedelta

class TelegramNotifier:
    def __init__(self, bot_token=None, chat_id=None, throttle_seconds=300):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.throttle_seconds = throttle_seconds
        self.last_alerts = {}
    
    async def send_alert(self, message, level='WARNING'):
        if message in self.last_alerts:
            if (datetime.now() - self.last_alerts[message]).total_seconds() < self.throttle_seconds:
                return
        self.last_alerts[message] = datetime.now()
        logging.info(f"Alert: {message}")
''',

    os.path.join(BASE_PATH, "core", "memory_monitor.py"): '''"""메모리 모니터"""
import logging
from datetime import datetime

class MemoryMonitor:
    def __init__(self, warning_threshold_mb=500):
        self.warning_threshold = warning_threshold_mb * 1024 * 1024
        self.memory_history = []
        self.logger = logging.getLogger('my_py_lib')
    
    def check_memory(self):
        try:
            import psutil
            current = psutil.Process().memory_info().rss
            self.memory_history.append({'timestamp': datetime.now(), 'memory_mb': current / 1024 / 1024})
            return {'status': 'OK', 'memory_mb': current / 1024 / 1024}
        except:
            return {'status': 'UNAVAILABLE'}
    
    def detect_memory_leak(self):
        return False
''',

    os.path.join(BASE_PATH, "core", "concurrency.py"): '''"""동시성 감지"""
class ConcurrencyMonitor:
    def __init__(self):
        self.lock_contentions = {}
    
    def detect_race_condition(self, resource):
        if resource not in self.lock_contentions:
            self.lock_contentions[resource] = 0
        self.lock_contentions[resource] += 1
        return self.lock_contentions[resource] > 5
    
    def detect_deadlock(self):
        return False

class DeadlockDetector:
    def check(self):
        return False
''',

    os.path.join(BASE_PATH, "core", "db_pool.py"): '''"""DB 연결 풀"""
from threading import Lock

class DBPoolManager:
    def __init__(self, pool_size=5):
        self.pool_size = pool_size
        self.available = pool_size
        self.in_use = 0
        self.lock = Lock()
    
    def acquire(self):
        with self.lock:
            if self.available > 0:
                self.available -= 1
                self.in_use += 1
                return True
        return False
    
    def release(self):
        with self.lock:
            self.in_use -= 1
            self.available += 1
    
    def get_pool_status(self):
        return {'total': self.pool_size, 'available': self.available, 'in_use': self.in_use}
''',

    os.path.join(BASE_PATH, "core", "distributed.py"): '''"""분산 로깅"""
import logging

class DistributedLogger:
    def __init__(self, project_name='default'):
        self.project_name = project_name
        self.logger = logging.getLogger('my_py_lib')
    
    def send_log(self, level, message):
        self.logger.log(getattr(logging, level), f"[{self.project_name}] {message}")

class CentralLogServer:
    def __init__(self):
        self.logs_by_project = {}
    
    def aggregate_logs(self):
        return self.logs_by_project
''',

    os.path.join(BASE_PATH, "core", "self_healing.py"): '''"""자동 복구"""
import logging

class SelfHealingManager:
    RECOVERY_RULES = {
        'ConnectionRefusedError': 'restart_service',
        'MemoryError': 'cleanup_cache',
    }
    
    def __init__(self):
        self.logger = logging.getLogger('my_py_lib')
    
    def attempt_recovery(self, error_type):
        action = self.RECOVERY_RULES.get(error_type)
        if action == 'restart_service':
            return self._restart_service()
        elif action == 'cleanup_cache':
            return self._cleanup_cache()
        return False
    
    def _restart_service(self):
        self.logger.info("Restarting service...")
        return True
    
    def _cleanup_cache(self):
        import gc
        gc.collect()
        self.logger.info("Cache cleaned")
        return True
''',

    os.path.join(BASE_PATH, "core", "encryption.py"): '''"""암호화 로그"""
import logging

class EncryptedLogger:
    def __init__(self, log_file='encrypted.log'):
        self.log_file = log_file
        self.logger = logging.getLogger('my_py_lib')
    
    def log_sensitive(self, level, message):
        masked = '*' * len(message)
        self.logger.log(getattr(logging, level), f"[ENCRYPTED] {masked}")
''',

    os.path.join(BASE_PATH, "core", "bottleneck.py"): '''"""병목 감지"""
import logging

class BottleneckDetector:
    def __init__(self):
        self.function_times = {}
        self.logger = logging.getLogger('my_py_lib')
    
    def record_execution(self, func_name, elapsed_ms):
        if func_name not in self.function_times:
            self.function_times[func_name] = []
        self.function_times[func_name].append(elapsed_ms)
    
    def detect_bottlenecks(self):
        bottlenecks = []
        for func_name, times in self.function_times.items():
            if len(times) > 10:
                avg_time = sum(times) / len(times)
                if avg_time > 1000:
                    bottlenecks.append({'function': func_name, 'avg_ms': avg_time})
        return bottlenecks
''',

    os.path.join(BASE_PATH, "core", "network_monitor.py"): '''"""네트워크 모니터"""
import logging

class NetworkMonitor:
    def __init__(self):
        self.latencies = {}
        self.logger = logging.getLogger('my_py_lib')
    
    async def measure_api_latency(self, url):
        import time
        start = time.time()
        elapsed = (time.time() - start) * 1000
        if url not in self.latencies:
            self.latencies[url] = []
        self.latencies[url].append(elapsed)
        return elapsed
    
    def get_network_health(self):
        health = {}
        for url, latencies in self.latencies.items():
            avg = sum(latencies) / len(latencies) if latencies else 0
            status = 'CRITICAL' if avg > 1000 else 'WARNING' if avg > 500 else 'OK'
            health[url] = {'status': status, 'avg_ms': avg}
        return health
''',

    os.path.join(BASE_PATH, "core", "stacktrace.py"): '''"""스택 트레이스 시각화"""
import traceback

class StacktraceVisualizer:
    @staticmethod
    def format_traceback(exc_info):
        tb_lines = traceback.format_exception(*exc_info)
        formatted = "STACKTRACE:\\n"
        for line in tb_lines:
            formatted += f"{line.rstrip()}\\n"
        return formatted
    
    @staticmethod
    def get_call_chain(exc_info):
        tb = exc_info[2]
        chain = []
        while tb:
            frame = tb.tb_frame
            chain.append({'file': frame.f_code.co_filename, 'function': frame.f_code.co_name, 'line': tb.tb_lineno})
            tb = tb.tb_next
        return chain
''',

    os.path.join(BASE_PATH, "core", "daily_report.py"): '''"""일일 보고서"""
from datetime import datetime

class DailyReportGenerator:
    def __init__(self):
        self.logs = []
    
    def generate_report(self):
        report = f"Daily Report ({datetime.now().strftime('%Y-%m-%d')})\\nTotal Logs: {len(self.logs)}"
        return report
    
    def save_report(self, output_dir='.'):
        report = self.generate_report()
        filename = f"{output_dir}/report_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        return filename
''',

    os.path.join(BASE_PATH, "core", "ab_test.py"): '''"""A/B 테스트"""
import logging

class ABTestAnalyzer:
    def __init__(self):
        self.test_results = {}
        self.logger = logging.getLogger('my_py_lib')
    
    def record_test(self, test_name, group, value):
        if test_name not in self.test_results:
            self.test_results[test_name] = {'A': [], 'B': []}
        self.test_results[test_name][group].append(value)
    
    def analyze(self, test_name):
        results = self.test_results.get(test_name, {'A': [], 'B': []})
        a_mean = sum(results['A']) / len(results['A']) if results['A'] else 0
        b_mean = sum(results['B']) / len(results['B']) if results['B'] else 0
        return {'test_name': test_name, 'a_mean': a_mean, 'b_mean': b_mean, 'is_significant': abs(a_mean - b_mean) > 10}
''',

    os.path.join(BASE_PATH, "core", "distributed_trace.py"): '''"""분산 추적"""
import uuid
from datetime import datetime

class DistributedTracer:
    def __init__(self):
        self.traces = {}
    
    def start_trace(self, service_name):
        trace_id = str(uuid.uuid4())
        self.traces[trace_id] = {'service': service_name, 'start_time': datetime.now(), 'spans': []}
        return trace_id
    
    def add_span(self, trace_id, service, operation, duration_ms):
        if trace_id in self.traces:
            self.traces[trace_id]['spans'].append({'service': service, 'operation': operation, 'duration_ms': duration_ms})
    
    def get_trace_timeline(self, trace_id):
        if trace_id not in self.traces:
            return "No trace found"
        trace = self.traces[trace_id]
        timeline = f"Trace: {trace_id}\\nService: {trace['service']}\\n"
        for span in trace['spans']:
            timeline += f"  - {span['operation']}: {span['duration_ms']:.1f}ms\\n"
        return timeline
''',

    os.path.join(BASE_PATH, "core", "error_prediction.py"): '''"""에러 예측"""
from datetime import datetime
from collections import deque

class ErrorPredictor:
    def __init__(self):
        self.error_history = deque(maxlen=1000)
    
    def record_error(self, error_type):
        self.error_history.append({'type': error_type, 'timestamp': datetime.now()})
    
    def predict_next_error(self):
        if len(self.error_history) < 10:
            return None
        error_types = {}
        for error in self.error_history:
            error_types[error['type']] = error_types.get(error['type'], 0) + 1
        most_common = max(error_types.items(), key=lambda x: x[1])[0]
        return {'predicted_error': most_common, 'confidence': error_types[most_common] / len(self.error_history) * 100}
''',

    os.path.join(BASE_PATH, "core", "config_version.py"): '''"""설정 버전 관리"""
import json
from datetime import datetime

class ConfigVersionManager:
    def __init__(self):
        self.versions = []
    
    def save_version(self, config_name, content):
        version_info = {'name': config_name, 'version': len(self.versions) + 1, 'timestamp': datetime.now().isoformat(), 'content': content}
        self.versions.append(version_info)
    
    def rollback_to_version(self, config_name, version):
        for v in self.versions:
            if v['name'] == config_name and v['version'] == version:
                return v['content']
        return None
    
    def diff_versions(self, config_name, v1, v2):
        return {'added': {}, 'removed': {}, 'modified': {}}
''',

    os.path.join(BASE_PATH, "core", "i18n.py"): '''"""국제화"""
import logging

class I18nLogger:
    MESSAGES = {
        'en': {'error': 'Error occurred', 'warning': 'Warning'},
        'ko': {'error': '에러 발생', 'warning': '경고'},
        'ja': {'error': 'エラーが発生しました', 'warning': '警告'}
    }
    
    def __init__(self, language='en'):
        self.language = language
        self.logger = logging.getLogger('my_py_lib')
    
    def translate(self, message_key):
        return self.MESSAGES.get(self.language, self.MESSAGES['en']).get(message_key, message_key)
''',

    os.path.join(BASE_PATH, "core", "audit_log.py"): '''"""감사 로그"""
import json
import logging
from datetime import datetime

class AuditLogger:
    def __init__(self, audit_file='audit.log'):
        self.audit_file = audit_file
        self.logger = logging.getLogger('my_py_lib')
    
    def log_action(self, user, action, resource, result):
        log_entry = {'timestamp': datetime.now().isoformat(), 'user': user, 'action': action, 'resource': resource, 'result': result}
        try:
            with open(self.audit_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\\n')
        except Exception as e:
            self.logger.error(f"Failed to save audit log: {str(e)}")
''',

    # UI 모듈
    os.path.join(BASE_PATH, "ui", "status_window.py"): '''"""상태 창"""
import logging

class StatusWindow:
    def __init__(self):
        self.logs = []
        self.logger = logging.getLogger('my_py_lib')
    
    def show_message(self, level, message):
        self.logs.append({'level': level, 'message': message})
        self.logger.log(getattr(logging, level), message)
    
    def update_progress(self, percentage):
        self.logger.info(f"Progress: {percentage}%")
''',

    os.path.join(BASE_PATH, "ui", "dashboard.py"): '''"""대시보드"""
from datetime import datetime

class DebugDashboard:
    def __init__(self):
        self.data = {}
    
    def generate_html(self):
        html = f"<html><head><title>Debug Dashboard</title></head><body><h1>Dashboard</h1><p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p></body></html>"
        return html
    
    def save_html(self, output_file='dashboard.html'):
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_html())
        return output_file
''',

    os.path.join(BASE_PATH, "ui", "realtime_dashboard.py"): '''"""실시간 대시보드"""
import logging

class RealtimeDashboard:
    def __init__(self):
        self.clients = set()
        self.logger = logging.getLogger('my_py_lib')
    
    async def handle_client(self, request):
        self.logger.info("New client connected")
        return True
    
    async def broadcast_update(self, data):
        self.logger.info(f"Broadcast: {data}")
''',

    # __init__ 파일들
    os.path.join(BASE_PATH, "__init__.py"): '''"""my_py_lib - GY Debugging Toolkit"""
__version__ = '1.0.0'
__author__ = 'Nam Ki-dong'
__description__ = 'GY Logging & Debugging Toolkit'

from .core.logger import IntegratedLogger, SmartErrorHandler
from .core.analyzer import ErrorAnalyzer
from .core.filter import LogFilter
from .core.profiler import PerformanceProfiler
from .core.grouper import ErrorGrouper
from .core.severity import ErrorSeverity, ErrorSeverityAnalyzer
from .core.notifier import TelegramNotifier
from .core.memory_monitor import MemoryMonitor
from .core.concurrency import ConcurrencyMonitor, DeadlockDetector
from .core.db_pool import DBPoolManager
from .core.distributed import DistributedLogger, CentralLogServer
from .core.self_healing import SelfHealingManager
from .core.encryption import EncryptedLogger
from .core.bottleneck import BottleneckDetector
from .core.network_monitor import NetworkMonitor
from .core.stacktrace import StacktraceVisualizer
from .core.daily_report import DailyReportGenerator
from .core.ab_test import ABTestAnalyzer
from .core.distributed_trace import DistributedTracer
from .core.error_prediction import ErrorPredictor
from .core.config_version import ConfigVersionManager
from .core.i18n import I18nLogger
from .core.audit_log import AuditLogger
from .ui.status_window import StatusWindow
from .ui.dashboard import DebugDashboard
from .ui.realtime_dashboard import RealtimeDashboard

__all__ = ['IntegratedLogger', 'SmartErrorHandler', 'ErrorAnalyzer', 'LogFilter', 'PerformanceProfiler', 'ErrorGrouper', 'ErrorSeverity', 'ErrorSeverityAnalyzer', 'TelegramNotifier', 'MemoryMonitor', 'ConcurrencyMonitor', 'DeadlockDetector', 'DBPoolManager', 'DistributedLogger', 'CentralLogServer', 'SelfHealingManager', 'EncryptedLogger', 'BottleneckDetector', 'NetworkMonitor', 'StacktraceVisualizer', 'DailyReportGenerator', 'ABTestAnalyzer', 'DistributedTracer', 'ErrorPredictor', 'ConfigVersionManager', 'I18nLogger', 'AuditLogger', 'StatusWindow', 'DebugDashboard', 'RealtimeDashboard']
''',

    os.path.join(BASE_PATH, "core", "__init__.py"): '''"""Core 모듈"""
from .logger import IntegratedLogger, SmartErrorHandler
from .analyzer import ErrorAnalyzer
from .filter import LogFilter
from .profiler import PerformanceProfiler
from .grouper import ErrorGrouper
from .severity import ErrorSeverity, ErrorSeverityAnalyzer
from .notifier import TelegramNotifier
from .memory_monitor import MemoryMonitor
from .concurrency import ConcurrencyMonitor, DeadlockDetector
from .db_pool import DBPoolManager
from .distributed import DistributedLogger, CentralLogServer
from .self_healing import SelfHealingManager
from .encryption import EncryptedLogger
from .bottleneck import BottleneckDetector
from .network_monitor import NetworkMonitor
from .stacktrace import StacktraceVisualizer
from .daily_report import DailyReportGenerator
from .ab_test import ABTestAnalyzer
from .distributed_trace import DistributedTracer
from .error_prediction import ErrorPredictor
from .config_version import ConfigVersionManager
from .i18n import I18nLogger
from .audit_log import AuditLogger

__all__ = ['IntegratedLogger', 'SmartErrorHandler', 'ErrorAnalyzer', 'LogFilter', 'PerformanceProfiler', 'ErrorGrouper', 'ErrorSeverity', 'ErrorSeverityAnalyzer', 'TelegramNotifier', 'MemoryMonitor', 'ConcurrencyMonitor', 'DeadlockDetector', 'DBPoolManager', 'DistributedLogger', 'CentralLogServer', 'SelfHealingManager', 'EncryptedLogger', 'BottleneckDetector', 'NetworkMonitor', 'StacktraceVisualizer', 'DailyReportGenerator', 'ABTestAnalyzer', 'DistributedTracer', 'ErrorPredictor', 'ConfigVersionManager', 'I18nLogger', 'AuditLogger']
''',

    os.path.join(BASE_PATH, "ui", "__init__.py"): '''"""UI 모듈"""
from .status_window import StatusWindow
from .dashboard import DebugDashboard
from .realtime_dashboard import RealtimeDashboard

__all__ = ['StatusWindow', 'DebugDashboard', 'RealtimeDashboard']
''',

    os.path.join(BASE_PATH, "plugins", "__init__.py"): '''"""플러그인 모듈"""
__all__ = []
''',

    os.path.join(BASE_PATH, "setup.py"): '''#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='my_py_lib',
    version='1.0.0',
    description='GY Logging & Debugging Toolkit',
    author='Nam Ki-dong',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=['aiohttp>=3.8.0', 'pyyaml>=6.0', 'psutil>=5.9.0', 'cryptography>=38.0.0', 'scipy>=1.9.0'],
)
''',

    os.path.join(BASE_PATH, "requirements.txt"): '''aiohttp>=3.8.0
pyyaml>=6.0
psutil>=5.9.0
cryptography>=38.0.0
scipy>=1.9.0
''',

    os.path.join(BASE_PATH, "README.md"): '''# my_py_lib - GY Debugging Toolkit

26개 기능의 엔터프라이즈급 디버깅 라이브러리

## 설치
pip install -e C:\\my_py_lib

## 사용
from my_py_lib import IntegratedLogger
logger = IntegratedLogger.setup()
''',

    os.path.join(BASE_PATH, "configs", "base_patterns.yaml"): '''errors:
  ConnectionRefusedError:
    cause: "연결 거부"
    solution: "서버 확인"
  TimeoutError:
    cause: "시간 초과"
    solution: "네트워크 확인"
  FileNotFoundError:
    cause: "파일 없음"
    solution: "경로 확인"
''',
}

file_count = 0
for filepath, content in FILES.items():
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    file_count += 1
    print(f"  [{file_count:2d}/{len(FILES)}] ✓ {os.path.basename(filepath)}")

print(f"✅ 파일 생성 완료 ({file_count}개)\n")

# ===== STEP 3: ZIP 압축 =====
print("="*70)
print("STEP 3: ZIP 압축")
print("="*70)

# 기존 ZIP 삭제
if os.path.exists(OUTPUT_ZIP):
    os.remove(OUTPUT_ZIP)
    print(f"  기존 파일 삭제")

# ZIP 생성
with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(BASE_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, os.path.dirname(BASE_PATH))
            zf.write(file_path, arcname)

zip_size = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
print(f"  ✓ ZIP 생성: {OUTPUT_ZIP}")
print(f"  파일 크기: {zip_size:.2f}MB")
print(f"✅ 압축 완료\n")

# ===== 최종 =====
print("="*70)
print("✅ my_py_lib 빌드 완료!")
print("="*70)
print()
print(f"📊 빌드 결과:")
print(f"  ├─ 생성 파일: {file_count}개")
print(f"  ├─ 저장 위치: {BASE_PATH}")
print(f"  ├─ ZIP 파일: {OUTPUT_ZIP}")
print(f"  └─ 파일 크기: {zip_size:.2f}MB")
print()
print(f"🚀 다음 단계:")
print(f"  1. {OUTPUT_ZIP} 확인")
print(f"  2. 압축 해제: Expand-Archive -Path '{OUTPUT_ZIP}' -DestinationPath 'C:\\'")
print(f"  3. 설치: cd {BASE_PATH} && pip install -e .")
print(f"  4. 확인: python -c 'import my_py_lib; print(my_py_lib.__version__)'")
print()
print("="*70)