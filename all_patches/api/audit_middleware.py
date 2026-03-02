"""
SQM v7.0.0-alpha — API 감사 로깅 미들웨어
==========================================
모든 API 요청/응답을 기록.
- SQLite audit_log 테이블
- JSON 파일 백업 (일별 로테이션)

기록 항목:
    - timestamp, method, path, user, role, status_code,
      response_time_ms, client_ip, user_agent
"""

import json
import logging
import os
import time
from datetime import date, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """API 요청/응답 감사 로깅."""

    def __init__(self, app, db=None, log_dir: str = ''):
        super().__init__(app)
        self.db = db
        self.log_dir = log_dir or os.path.join(os.getcwd(), 'data', 'audit')
        os.makedirs(self.log_dir, exist_ok=True)
        self._ensure_table()

    def _ensure_table(self):
        """audit_log 테이블 생성."""
        if not self.db:
            return
        try:
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    role TEXT DEFAULT '',
                    status_code INTEGER DEFAULT 0,
                    response_time_ms REAL DEFAULT 0,
                    client_ip TEXT DEFAULT '',
                    user_agent TEXT DEFAULT '',
                    request_body TEXT DEFAULT '',
                    error_detail TEXT DEFAULT ''
                )
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp)
            """)
            self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_username
                ON audit_log(username)
            """)
            self.db.commit()
        except Exception as e:
            logger.debug(f"[Audit] 테이블 생성 실패: {e}")

    async def dispatch(self, request: Request, call_next) -> Response:
        # WebSocket, static, docs 제외
        path = request.url.path
        if path.startswith('/ws/') or path in ('/docs', '/redoc', '/openapi.json'):
            return await call_next(request)

        start = time.time()
        username = ''
        role = ''

        # 사용자 정보 추출
        auth = request.headers.get('authorization', '')
        if auth.startswith('Bearer '):
            try:
                from api.auth import verify_token
                payload = verify_token(auth[7:])
                if payload:
                    username = payload.get('sub', '')
                    role = payload.get('role', '')
            except Exception:
                pass

        # 요청 본문 (POST만, 크기 제한)
        request_body = ''
        if request.method in ('POST', 'PUT', 'PATCH'):
            try:
                body = await request.body()
                if len(body) < 4096:
                    request_body = body.decode('utf-8', errors='replace')
            except Exception:
                pass

        # 실행
        error_detail = ''
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            error_detail = str(e)[:500]
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            client_ip = request.client.host if request.client else ''
            user_agent = request.headers.get('user-agent', '')[:200]

            entry = {
                'timestamp': datetime.now().isoformat(),
                'method': request.method,
                'path': path,
                'username': username,
                'role': role,
                'status_code': status_code,
                'response_time_ms': round(elapsed_ms, 1),
                'client_ip': client_ip,
                'user_agent': user_agent,
                'request_body': request_body[:1000] if request.method == 'POST' else '',
                'error_detail': error_detail,
            }

            # DB 기록
            self._log_to_db(entry)

            # JSON 파일 기록
            self._log_to_file(entry)

            # 콘솔 로그 (간략)
            level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(level,
                f"[Audit] {request.method} {path} → {status_code} "
                f"({elapsed_ms:.0f}ms) user={username or 'anon'}")

        return response

    def _log_to_db(self, entry: dict):
        if not self.db:
            return
        try:
            self.db.execute("""
                INSERT INTO audit_log
                (timestamp, method, path, username, role, status_code,
                 response_time_ms, client_ip, user_agent, request_body, error_detail)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry['timestamp'], entry['method'], entry['path'],
                entry['username'], entry['role'], entry['status_code'],
                entry['response_time_ms'], entry['client_ip'],
                entry['user_agent'], entry['request_body'], entry['error_detail'],
            ))
            self.db.commit()
        except Exception as e:
            logger.debug(f"[Audit] DB 기록 실패: {e}")

    def _log_to_file(self, entry: dict):
        try:
            today = date.today().isoformat()
            path = os.path.join(self.log_dir, f'audit_{today}.jsonl')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.debug(f"[Audit] 파일 기록 실패: {e}")


# ═══════════════════════════════════════════
# 감사 조회 API (admin 전용)
# ═══════════════════════════════════════════

def get_audit_logs(db, start_date: str = '', end_date: str = '',
                   username: str = '', method: str = '',
                   limit: int = 100) -> list:
    """감사 로그 조회."""
    where = ["1=1"]
    params = []
    if start_date:
        where.append("timestamp >= ?")
        params.append(start_date)
    if end_date:
        where.append("timestamp <= ?")
        params.append(end_date + 'T23:59:59')
    if username:
        where.append("username = ?")
        params.append(username)
    if method:
        where.append("method = ?")
        params.append(method.upper())

    rows = db.fetchall(f"""
        SELECT timestamp, method, path, username, role, status_code,
               response_time_ms, client_ip
        FROM audit_log
        WHERE {" AND ".join(where)}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """, tuple(params))
    return [dict(r) if isinstance(r, dict) else {
        'timestamp': r[0], 'method': r[1], 'path': r[2],
        'username': r[3], 'role': r[4], 'status_code': r[5],
        'response_time_ms': r[6], 'client_ip': r[7],
    } for r in (rows or [])]
