"""
SQM v7.0.0-alpha — JWT 인증 미들웨어
======================================
FastAPI 엔드포인트에 Bearer 토큰 기반 인증 추가.

사용법:
    # api/main.py에서 임포트
    from api.auth import get_current_user, create_access_token, router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

    # 보호된 엔드포인트
    @app.get("/api/v1/protected")
    def protected(user: dict = Depends(get_current_user)):
        return {"message": f"Hello {user['username']}"}
"""

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import b64decode, b64encode
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════

# 비밀키 (프로덕션에서는 환경변수 또는 secrets 파일 사용)
SECRET_KEY = os.environ.get('SQM_JWT_SECRET', 'sqm-dev-secret-change-in-production-2026')
TOKEN_EXPIRY = int(os.environ.get('SQM_TOKEN_EXPIRY', 86400))  # 24시간 (초)

# 역할 정의
ROLES = {
    'admin': {'level': 100, 'label': '관리자'},
    'operator': {'level': 50, 'label': '운영자'},
    'viewer': {'level': 10, 'label': '뷰어'},
}

# 기본 사용자 (프로덕션에서는 DB 사용)
DEFAULT_USERS = {
    'admin': {'password_hash': '', 'role': 'admin', 'name': '관리자'},
    'operator': {'password_hash': '', 'role': 'operator', 'name': '운영자'},
    'viewer': {'password_hash': '', 'role': 'viewer', 'name': '뷰어'},
}


# ═══════════════════════════════════════════
# 간이 JWT (외부 의존성 없음)
# ═══════════════════════════════════════════

def _b64url_encode(data: bytes) -> str:
    return b64encode(data).rstrip(b'=').replace(b'+', b'-').replace(b'/', b'_').decode()


def _b64url_decode(s: str) -> bytes:
    s = s.replace('-', '+').replace('_', '/')
    pad = 4 - len(s) % 4
    if pad != 4:
        s += '=' * pad
    return b64decode(s)


def _sign(payload: str) -> str:
    return _b64url_encode(hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).digest())


def create_access_token(username: str, role: str, name: str = '') -> str:
    """JWT 토큰 생성."""
    header = _b64url_encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode())
    payload_data = {
        'sub': username,
        'role': role,
        'name': name,
        'iat': int(time.time()),
        'exp': int(time.time()) + TOKEN_EXPIRY,
    }
    payload = _b64url_encode(json.dumps(payload_data).encode())
    signature = _sign(f"{header}.{payload}")
    return f"{header}.{payload}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """JWT 토큰 검증. 유효하면 payload, 아니면 None."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header, payload, signature = parts

        # 서명 검증
        expected = _sign(f"{header}.{payload}")
        if not hmac.compare_digest(signature, expected):
            logger.warning("[Auth] 서명 불일치")
            return None

        # 만료 검증
        payload_data = json.loads(_b64url_decode(payload))
        if payload_data.get('exp', 0) < time.time():
            logger.info("[Auth] 토큰 만료")
            return None

        return payload_data
    except Exception as e:
        logger.debug(f"[Auth] 토큰 검증 실패: {e}")
        return None


def hash_password(password: str) -> str:
    """SHA-256 비밀번호 해시."""
    return hashlib.sha256(f"{SECRET_KEY}:{password}".encode()).hexdigest()


# ═══════════════════════════════════════════
# FastAPI 인증 의존성
# ═══════════════════════════════════════════

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """현재 인증된 사용자 반환. 미인증 시 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 필요: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def require_role(min_role: str = 'viewer'):
    """역할 기반 접근 제어 의존성."""
    min_level = ROLES.get(min_role, {}).get('level', 0)

    def checker(user: dict = Depends(get_current_user)):
        user_level = ROLES.get(user.get('role', ''), {}).get('level', 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한 부족: {min_role} 이상 필요 (현재: {user.get('role', 'unknown')})",
            )
        return user

    return checker


# ═══════════════════════════════════════════
# 인증 라우터
# ═══════════════════════════════════════════

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserInfoResponse(BaseModel):
    username: str
    role: str
    name: str
    role_label: str


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """로그인 → JWT 토큰 발급."""
    user = DEFAULT_USERS.get(req.username)
    if not user:
        raise HTTPException(400, "사용자를 찾을 수 없습니다")

    # 비밀번호 해시가 비어있으면 초기 설정 (개발용 — username == password)
    if not user['password_hash']:
        user['password_hash'] = hash_password(req.username)

    if user['password_hash'] != hash_password(req.password):
        raise HTTPException(401, "비밀번호가 일치하지 않습니다")

    token = create_access_token(req.username, user['role'], user.get('name', ''))
    return TokenResponse(
        access_token=token,
        expires_in=TOKEN_EXPIRY,
        user={'username': req.username, 'role': user['role'], 'name': user.get('name', '')},
    )


@router.get("/me", response_model=UserInfoResponse)
def get_me(user: dict = Depends(get_current_user)):
    """현재 사용자 정보."""
    role = user.get('role', 'viewer')
    return UserInfoResponse(
        username=user.get('sub', ''),
        role=role,
        name=user.get('name', ''),
        role_label=ROLES.get(role, {}).get('label', '알 수 없음'),
    )


@router.post("/change-password")
def change_password(
    current_password: str,
    new_password: str,
    user: dict = Depends(get_current_user),
):
    """비밀번호 변경."""
    username = user.get('sub', '')
    user_data = DEFAULT_USERS.get(username)
    if not user_data:
        raise HTTPException(404, "사용자 없음")
    if user_data['password_hash'] != hash_password(current_password):
        raise HTTPException(401, "현재 비밀번호 불일치")
    user_data['password_hash'] = hash_password(new_password)
    return {"message": "비밀번호가 변경되었습니다"}
