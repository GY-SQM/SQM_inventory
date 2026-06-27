import os
import re

# 디자인 시스템 변수와 일치하지 않는 HEX 색상값을 찾아내는 스크립트
def audit_ui_legacy():
    # HEX 컬러 패턴
    hex_pattern = re.compile(r'#[0-9a-fA-F]{6}')
    legacy_files = []
    
    for root, _, files in os.walk("gui_app_modular"):
        for file in files:
            if file.endswith(('.py', '.json')):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if hex_pattern.search(content):
                        legacy_files.append(path)
    
    return legacy_files

print(audit_ui_legacy())
