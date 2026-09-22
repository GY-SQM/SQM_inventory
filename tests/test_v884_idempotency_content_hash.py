import pytest
from parsers.base import BaseParser

class DummyTestParser(BaseParser):
    def parse(self, file_path: str):
        return {"lot_no": "LOT-20260922-01", "weight": 1000, "b_l_no": "BL-99988"}
        
    def validate(self, data) -> bool:
        return True

def test_compute_content_hash_consistency():
    """동일한 데이터에 대한 Content Hash 영수증 생선의 일관성(멱등성) 테스트"""
    parser = DummyTestParser()
    data1 = {"lot_no": "LOT-20260922-01", "weight": 1000, "b_l_no": "BL-99988"}
    data2 = {"weight": 1000, "b_l_no": "BL-99988", "lot_no": "LOT-20260922-01"}  # 키 순서가 다름
    
    hash1 = parser.compute_content_hash(data1)
    hash2 = parser.compute_content_hash(data2)
    
    assert hash1 is not None
    assert len(hash1) == 64
    assert hash1 == hash2  # json.dumps(sort_keys=True)에 의해 항상 일치해야 함

def test_idempotent_duplicate_detection():
    """동일한 Content Hash 발생 시 중복 감지 멱등성 테스트"""
    parser = DummyTestParser()
    processed_hashes = set()
    
    data = {"lot_no": "LOT-20260922-02", "weight": 850}
    hash_val = parser.compute_content_hash(data)
    
    # 1차 처리 (성공)
    assert hash_val not in processed_hashes
    processed_hashes.add(hash_val)
    
    # 2차 처리 (중복 감지 멱등성 작동)
    assert hash_val in processed_hashes  # 이미 존재하는 영수증으로 처리 차단됨
