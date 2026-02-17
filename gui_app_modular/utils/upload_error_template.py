# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 업로드 실패 메시지 템플릿
================================================

v4.2.1: 상세한 오류 메시지 및 해결 방법 제공

작성자: Ruby
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UploadErrorTemplate:
    """업로드 실패 메시지 템플릿"""
    
    # ========================================
    # 오류 타입별 템플릿
    # ========================================
    
    ERROR_TEMPLATES = {
        'missing_lot_no': {
            'title': 'LOT NO 누락',
            'description': 'LOT NO 컬럼이 비어있거나 누락되었습니다.',
            'solution': [
                'LOT NO는 10자리 숫자 필수입니다.',
                '예시: 1125072340',
                '빈 셀이 없는지 확인하세요.'
            ],
            'example': '1125072340'
        },
        
        'invalid_lot_no': {
            'title': 'LOT NO 형식 오류',
            'description': 'LOT NO가 올바른 형식이 아닙니다.',
            'solution': [
                'LOT NO는 정확히 10자리 숫자여야 합니다.',
                '문자, 공백, 특수문자 불가',
                '예시: 1125072340'
            ],
            'example': '1125072340 (O) / 112-507-2340 (X)'
        },
        
        'missing_date': {
            'title': '날짜 누락',
            'description': '필수 날짜 컬럼이 비어있습니다.',
            'solution': [
                '날짜 형식: YYYY-MM-DD',
                '예시: 2025-01-15',
                '빈 셀이 없는지 확인하세요.'
            ],
            'example': '2025-01-15'
        },
        
        'invalid_date': {
            'title': '날짜 형식 오류',
            'description': '날짜가 올바른 형식이 아닙니다.',
            'solution': [
                '형식: YYYY-MM-DD (년-월-일)',
                '월: 01~12, 일: 01~31',
                '예시: 2025-01-15',
                '슬래시(/) 대신 하이픈(-) 사용'
            ],
            'example': '2025-01-15 (O) / 2025/01/15 (X) / 20250115 (X)'
        },
        
        'missing_required': {
            'title': '필수 컬럼 누락',
            'description': '아래 "실패 행"에서 어떤 행의 어떤 항목이 비어 있는지 확인한 뒤, 해당 셀을 채워 주세요.',
            'solution': [
                '필수 컬럼: LOT NO, PRODUCT, NET(Kg), MXBG',
                '실패 행에 표시된 항목만 채우면 됩니다.',
                '빈 셀이 없는지 확인하세요.'
            ],
            'example': 'LOT NO: 1125072340\nPRODUCT: LITHIUM CARBONATE\nNET(Kg): 25000\nMXBG: 10'
        },
        
        'invalid_number': {
            'title': '숫자 형식 오류',
            'description': '숫자 컬럼에 잘못된 값이 입력되었습니다.',
            'solution': [
                '숫자만 입력 가능합니다.',
                '쉼표(,) 제거: 25,000 → 25000',
                '문자 제거: 25톤 → 25000',
                '소수점: 25.5 (가능)'
            ],
            'example': '25000 (O) / 25,000 (X) / 25톤 (X)'
        },
        
        'duplicate_lot': {
            'title': 'LOT NO 중복',
            'description': '이미 존재하는 LOT NO입니다.',
            'solution': [
                'LOT NO는 고유해야 합니다.',
                '기존 재고를 확인하세요.',
                '새로운 LOT NO를 사용하세요.',
                '재고 탭에서 기존 LOT 검색 가능'
            ],
            'example': '기존 LOT: 1125072340\n신규 LOT: 1125072341'
        },
        
        'file_format': {
            'title': '파일 형식 오류',
            'description': 'Excel 파일을 읽을 수 없습니다.',
            'solution': [
                'Excel 파일(.xlsx, .xls)만 가능합니다.',
                '파일이 손상되지 않았는지 확인하세요.',
                'Excel에서 파일을 열어 확인하세요.',
                '다른 이름으로 저장 후 재시도'
            ],
            'example': 'file.xlsx (O) / file.csv (X) / file.txt (X)'
        },
        
        'encoding': {
            'title': '인코딩 오류',
            'description': '파일의 문자 인코딩이 올바르지 않습니다.',
            'solution': [
                'Excel에서 "다른 이름으로 저장"',
                '파일 형식: Excel 통합 문서(.xlsx)',
                '한글이 깨지지 않는지 확인',
                '메모장으로 열어보지 마세요'
            ],
            'example': 'UTF-8 인코딩 권장'
        },
        
        'column_header': {
            'title': '컬럼명 오류',
            'description': '필수 컬럼명을 찾을 수 없습니다.',
            'solution': [
                '첫 번째 행에 컬럼명이 있어야 합니다.',
                '필수 컬럼: LOT NO, PRODUCT, NET(Kg), MXBG',
                '컬럼명 철자를 정확히 입력하세요.',
                '대소문자 구분 없음'
            ],
            'example': 'LOT NO (O) / Lot No (O) / 로트번호 (X)'
        }
    }
    
    @classmethod
    def format_error_message(
        cls, 
        error_type: str, 
        failed_rows: List[Dict],
        total_rows: int = 0
    ) -> Dict:
        """
        오류 메시지 포맷팅
        
        Args:
            error_type: 오류 타입 키
            failed_rows: 실패한 행 정보 리스트
                [{'row': 2, 'value': '112507234', 'column': 'LOT NO'}, ...]
            total_rows: 전체 행 수
            
        Returns:
            포맷팅된 오류 메시지 딕셔너리
        """
        template = cls.ERROR_TEMPLATES.get(error_type, {
            'title': '알 수 없는 오류',
            'description': '파일 처리 중 오류가 발생했습니다.',
            'solution': ['파일을 확인하고 다시 시도하세요.'],
            'example': ''
        })
        
        # 실패 행 상세 정보 생성 — 어느 행의 어떤 데이터가 빠졌는지 명확히 표시
        failed_details = []
        for item in failed_rows[:10]:  # 최대 10개만 표시
            row_num = item.get('row', item.get('row_num', '?'))
            value = item.get('value', '')
            column = item.get('column', '')
            missing_columns = item.get('missing_columns', [])  # ['LOT NO', 'PRODUCT'] 등
            
            if missing_columns:
                cols_str = ', '.join(missing_columns)
                failed_details.append(f"  • 행 {row_num}: [{cols_str}] 비어 있음")
            elif column:
                failed_details.append(f"  • 행 {row_num}, {column}: {value}")
            else:
                failed_details.append(f"  • 행 {row_num}: {value}")
        
        if len(failed_rows) > 10:
            failed_details.append(f"  • ... 외 {len(failed_rows) - 10}건")
        
        return {
            'title': template['title'],
            'description': template['description'],
            'failed_count': len(failed_rows),
            'total_rows': total_rows,
            'failed_details': '\n'.join(failed_details),
            'solution': template['solution'],
            'example': template['example']
        }
    
    @classmethod
    def format_multiple_errors(
        cls,
        errors: List[Dict],
        total_rows: int = 0
    ) -> str:
        """
        여러 오류를 하나의 메시지로 포맷팅
        
        Args:
            errors: 오류 정보 리스트
                [{'type': 'missing_lot_no', 'rows': [...]}, ...]
            total_rows: 전체 행 수
            
        Returns:
            포맷팅된 전체 메시지
        """
        if not errors:
            return "알 수 없는 오류가 발생했습니다."
        
        total_failed = sum(len(e.get('rows', [])) for e in errors)
        
        message_parts = []
        message_parts.append(f"{'='*50}")
        message_parts.append(f"📋 업로드 실패 요약")
        message_parts.append(f"{'='*50}")
        message_parts.append(f"전체 행: {total_rows}개")
        message_parts.append(f"실패: {total_failed}개")
        message_parts.append(f"성공: {total_rows - total_failed}개")
        message_parts.append("")
        
        for idx, error in enumerate(errors, 1):
            error_type = error.get('type', 'unknown')
            failed_rows = error.get('rows', [])
            
            formatted = cls.format_error_message(error_type, failed_rows, total_rows)
            
            message_parts.append(f"{'-'*50}")
            message_parts.append(f"❌ {idx}. {formatted['title']} ({formatted['failed_count']}건)")
            message_parts.append(f"{'-'*50}")
            message_parts.append(f"{formatted['description']}")
            message_parts.append("")
            message_parts.append("실패 행:")
            message_parts.append(formatted['failed_details'])
            message_parts.append("")
            message_parts.append("💡 해결 방법:")
            for solution in formatted['solution']:
                message_parts.append(f"  • {solution}")
            message_parts.append("")
            if formatted['example']:
                message_parts.append("📌 예시:")
                message_parts.append(f"  {formatted['example']}")
            message_parts.append("")
        
        message_parts.append(f"{'='*50}")
        message_parts.append("📞 추가 도움이 필요하면 관리자에게 문의하세요.")
        message_parts.append(f"{'='*50}")
        
        return '\n'.join(message_parts)


# 사용 예시
if __name__ == '__main__':
    # 예시 1: 단일 오류
    errors = [{
        'type': 'missing_lot_no',
        'rows': [
            {'row': 2, 'value': '', 'column': 'LOT NO'},
            {'row': 5, 'value': '', 'column': 'LOT NO'},
        ]
    }]
    
    msg = UploadErrorTemplate.format_multiple_errors(errors, total_rows=10)
    logger.debug(f"{msg}")
    
    # 예시 2: 복수 오류
    errors = [
        {
            'type': 'missing_lot_no',
            'rows': [
                {'row': 2, 'value': '', 'column': 'LOT NO'},
                {'row': 5, 'value': '', 'column': 'LOT NO'},
            ]
        },
        {
            'type': 'invalid_date',
            'rows': [
                {'row': 3, 'value': '2025-13-01', 'column': 'ARRIVAL'},
                {'row': 6, 'value': '20250101', 'column': 'ARRIVAL'},
            ]
        }
    ]
    
    msg = UploadErrorTemplate.format_multiple_errors(errors, total_rows=10)
    logger.debug(f"{msg}")
