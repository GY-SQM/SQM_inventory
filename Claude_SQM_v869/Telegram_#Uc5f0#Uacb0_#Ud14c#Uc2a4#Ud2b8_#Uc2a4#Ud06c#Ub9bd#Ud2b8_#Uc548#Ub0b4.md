# Telegram 연결 테스트 스크립트 안내
생성일: 2026-04-04 00:20

## 목적
현재 BOT_TOKEN / CHAT_ID 로 Telegram 전송이 되는지 가장 빠르게 확인한다.

---

## 1. 테스트용 Python 코드
아래 코드를 `scripts/test_telegram_connection.py` 로 저장한다.

```python
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN 또는 CHAT_ID가 비어 있습니다.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": "✅ Telegram 연결 테스트 성공 - SQM 자동화 브릿지"
        },
        timeout=20,
    )
    print("status:", res.status_code)
    print("body:", res.text)

if __name__ == "__main__":
    main()
```

---

## 2. 실행 방법
```bash
python scripts/test_telegram_connection.py
```

---

## 3. 성공 기준
- 텔레그램으로 테스트 메시지 도착
- 콘솔 status 가 200

---

## 4. 실패 시 점검
1. BOT_TOKEN 오타
2. CHAT_ID 오타
3. 봇이 해당 채팅에 메시지 보낼 권한이 있는지
4. 인터넷 연결
5. requests 설치 여부