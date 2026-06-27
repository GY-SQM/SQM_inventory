import pyautogui
import os
import datetime
import sys

def capture_ui(snapshot_name="ui_snapshot"):
    # 스냅샷 저장 디렉토리 생성
    save_dir = os.path.join(os.getcwd(), "docs", "ui_snapshots")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 시간 기반 파일명 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{snapshot_name}_{timestamp}.png"
    filepath = os.path.join(save_dir, filename)
    
    # 화면 캡처
    screenshot = pyautogui.screenshot()
    screenshot.save(filepath)
    
    print(f"Captured: {filepath}")
    return filepath

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "sqm_ui"
    capture_ui(name)
