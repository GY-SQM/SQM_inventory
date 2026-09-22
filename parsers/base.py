"""
SQM 재고관리 - 파서 기본 클래스
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class BaseParser(ABC):
    """파서 기본 클래스"""

    def __init__(self):
        self.source_file: Optional[str] = None
        self.errors: list = []

    @abstractmethod
    def parse(self, file_path: str) -> Any:
        """파일 파싱 (서브클래스에서 구현)"""
        raise NotImplementedError("하위 클래스에서 구현 필요")

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """데이터 유효성 검증"""
        raise NotImplementedError("하위 클래스에서 구현 필요")

    def get_file_extension(self, file_path: str) -> str:
        """파일 확장자 반환"""
        return Path(file_path).suffix.lower()

    def add_error(self, message: str):
        """에러 추가"""
        self.errors.append(message)

    def clear_errors(self):
        """에러 초기화"""
        self.errors.clear()

    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    def compute_content_hash(self, data: Any) -> str:
        """파싱 데이터 또는 원본의 SHA-256 Content Hash 계산 (멱등성 검증용 영수증 발급)"""
        import hashlib
        import json
        if isinstance(data, (dict, list)):
            dumped = json.dumps(data, sort_keys=True, default=str)
        else:
            dumped = str(data)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

