# -*- coding: utf-8 -*-
"""P3-6: 백업/복원 API"""
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from react_api.utils.db import get_db, now_str

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backup", tags=["backup"])

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "db" / "sqm_inventory.db"
BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "backups"


class BackupCreate(BaseModel):
    memo: str = ''


class RestoreRequest(BaseModel):
    filename: str


@router.post("/create")
def create_backup(req: BackupCreate = BackupCreate()):
    """DB 백업 생성"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        raise HTTPException(404, "DB 파일 없음")

    dt = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = BACKUP_DIR / f"sqm_backup_{dt}.db"
    shutil.copy2(DB_PATH, dest)

    # 메모 파일
    if req.memo:
        memo_file = dest.with_suffix('.memo')
        memo_file.write_text(req.memo, encoding='utf-8')

    size_mb = round(dest.stat().st_size / 1024 / 1024, 2)
    return {"success": True, "message": f"백업 생성: {dest.name} ({size_mb}MB)", "filename": dest.name}


@router.get("/list")
def list_backups():
    """백업 목록"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    for f in sorted(BACKUP_DIR.glob("sqm_backup_*.db"), reverse=True):
        memo = ''
        memo_file = f.with_suffix('.memo')
        if memo_file.exists():
            memo = memo_file.read_text(encoding='utf-8').strip()
        backups.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            "memo": memo,
        })
    return {"success": True, "backups": backups, "total": len(backups)}


@router.post("/restore")
def restore_backup(req: RestoreRequest):
    """백업 복원 (R10: 자동 백업 후 복원)"""
    # 경로 순회 공격 차단
    if '..' in req.filename or '/' in req.filename or '\\' in req.filename:
        raise HTTPException(400, "잘못된 파일명")

    src = BACKUP_DIR / req.filename
    if not src.exists():
        raise HTTPException(404, f"백업 파일 없음: {req.filename}")

    # R10: 복원 전 자동 백업
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dt = datetime.now().strftime('%Y%m%d_%H%M%S')
    auto_backup = BACKUP_DIR / f"sqm_auto_before_restore_{dt}.db"
    shutil.copy2(DB_PATH, auto_backup)

    # 복원
    shutil.copy2(src, DB_PATH)

    # WAL/SHM 삭제
    for ext in ('.db-wal', '.db-shm'):
        wal = DB_PATH.with_suffix(ext)
        if wal.exists():
            wal.unlink()

    return {"success": True, "message": f"복원 완료: {req.filename} (자동 백업: {auto_backup.name})"}


@router.get("/download/{filename}")
def download_backup(filename: str):
    """백업 파일 다운로드"""
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(400, "잘못된 파일명")
    path = BACKUP_DIR / filename
    if not path.exists():
        raise HTTPException(404, "파일 없음")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@router.delete("/{filename}")
def delete_backup(filename: str):
    """백업 삭제"""
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(400, "잘못된 파일명")
    path = BACKUP_DIR / filename
    if not path.exists():
        raise HTTPException(404, "파일 없음")
    path.unlink()
    memo = path.with_suffix('.memo')
    if memo.exists():
        memo.unlink()
    return {"success": True, "message": f"삭제: {filename}"}
