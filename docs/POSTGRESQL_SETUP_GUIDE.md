# PostgreSQL 설치 및 설정 가이드
## SQM 재고관리 시스템 v3.4.0

---

## 📋 목차

1. [PostgreSQL 설치 (Windows)](#1-postgresql-설치-windows)
2. [데이터베이스 생성](#2-데이터베이스-생성)
3. [Python 드라이버 설치](#3-python-드라이버-설치)
4. [SQM 설정](#4-sqm-설정)
5. [연결 테스트](#5-연결-테스트)
6. [서버 이전 방법](#6-서버-이전-방법-a--c)
7. [문제 해결](#7-문제-해결)

---

## 1. PostgreSQL 설치 (Windows)

### 다운로드
1. https://www.postgresql.org/download/windows/ 접속
2. **Download the installer** 클릭
3. 최신 버전 (16.x) 다운로드

### 설치
1. 다운로드한 파일 실행
2. 설치 경로: 기본값 유지 (`C:\Program Files\PostgreSQL\16`)
3. **컴포넌트 선택**:
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (관리 도구)
   - ✅ Command Line Tools
4. **Data Directory**: 기본값 유지
5. **비밀번호 설정**: `postgres` (또는 원하는 비밀번호)
   
   ⚠️ **중요**: 이 비밀번호를 기억하세요!
   
6. **포트**: `5432` (기본값)
7. **Locale**: Korean, Korea (또는 기본값)
8. 설치 완료!

### 환경변수 설정 (선택)
```
Path에 추가: C:\Program Files\PostgreSQL\16\bin
```

---

## 2. 데이터베이스 생성

### 방법 A: pgAdmin 사용 (GUI)

1. **pgAdmin 4** 실행 (시작메뉴에서 검색)
2. **Servers** → **PostgreSQL 16** 클릭
3. 비밀번호 입력 (설치 시 설정한 것)
4. **Databases** 우클릭 → **Create** → **Database**
5. 다음 입력:
   - **Database**: `sqm_inventory`
   - **Owner**: `postgres`
   - **Encoding**: `UTF8`
6. **Save** 클릭

### 방법 B: 명령줄 사용

```bash
# 명령 프롬프트 (관리자)
cd "C:\Program Files\PostgreSQL\16\bin"

# 데이터베이스 생성
createdb -U postgres sqm_inventory

# 비밀번호 입력 후 완료
```

### 방법 C: SQL 사용

```sql
-- psql 또는 pgAdmin Query Tool에서 실행
CREATE DATABASE sqm_inventory
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'Korean_Korea.949'
    LC_CTYPE = 'Korean_Korea.949'
    CONNECTION LIMIT = -1;
```

---

## 3. Python 드라이버 설치

### psycopg2 설치

```bash
# 명령 프롬프트
pip install psycopg2-binary
```

### 확인

```python
# Python에서 테스트
import psycopg2
print("psycopg2 설치 완료!")
```

---

## 4. SQM 설정

### 방법 A: 환경변수 설정 (권장)

```batch
:: Windows 환경변수 설정 (영구)
setx SQM_DB_TYPE postgresql
setx SQM_PG_HOST localhost
setx SQM_PG_PORT 5432
setx SQM_PG_DATABASE sqm_inventory
setx SQM_PG_USER postgres
setx SQM_PG_PASSWORD postgres
```

### 방법 B: config.py 직접 수정

```python
# config.py 에서

# DB_TYPE 변경
DB_TYPE = 'postgresql'  # 'sqlite' → 'postgresql'

# PostgreSQL 설정
PG_HOST = 'localhost'
PG_PORT = 5432
PG_DATABASE = 'sqm_inventory'
PG_USER = 'postgres'
PG_PASSWORD = 'your_password'  # 설치 시 설정한 비밀번호
```

---

## 5. 연결 테스트

### 테스트 스크립트 실행

```bash
python test_postgresql.py
```

### 수동 테스트

```python
# Python에서 직접 테스트
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='sqm_inventory',
    user='postgres',
    password='postgres'
)

cursor = conn.cursor()
cursor.execute("SELECT version()")
print(cursor.fetchone())

conn.close()
print("PostgreSQL 연결 성공!")
```

### SQM 실행

```bash
python run.py
```

정상이면 다음 메시지 표시:
```
✅ PostgreSQL 연결 완료: localhost:5432/sqm_inventory
SQMInventoryEngineV3 initialized: postgresql://postgres@localhost:5432/sqm_inventory
```

---

## 6. 서버 이전 방법 (A → C)

### 현재 상태
- **A (로컬)**: localhost에서 PostgreSQL 실행 중

### 서버로 이전 시

1. **서버에 PostgreSQL 설치** (동일 과정)

2. **데이터 백업 (로컬)**
```bash
pg_dump -U postgres sqm_inventory > sqm_backup.sql
```

3. **백업 파일을 서버로 복사**

4. **서버에서 복원**
```bash
psql -U postgres -d sqm_inventory < sqm_backup.sql
```

5. **설정 변경**
```python
# config.py 또는 환경변수
PG_HOST = '192.168.1.100'  # 서버 IP로 변경
```

6. **완료!** 코드 수정 없음

---

## 7. 문제 해결

### 연결 오류: "could not connect to server"

**원인**: PostgreSQL 서비스 미실행

**해결**:
```batch
:: 서비스 시작
net start postgresql-x64-16
```

또는 **서비스 관리자**에서 **postgresql-x64-16** 시작

### 연결 오류: "password authentication failed"

**원인**: 비밀번호 불일치

**해결**:
1. pgAdmin에서 비밀번호 확인
2. config.py의 PG_PASSWORD 수정

### 연결 오류: "database does not exist"

**원인**: sqm_inventory 데이터베이스 미생성

**해결**: [2. 데이터베이스 생성](#2-데이터베이스-생성) 참조

### psycopg2 import 오류

**원인**: 드라이버 미설치

**해결**:
```bash
pip install psycopg2-binary
```

### SQLite로 되돌리기

```python
# config.py에서
DB_TYPE = 'sqlite'  # postgresql → sqlite
```

---

## 📊 PostgreSQL vs SQLite 비교

| 항목 | SQLite | PostgreSQL |
|------|--------|------------|
| 동시 접속 | 제한적 | ✅ 무제한 |
| 데이터 규모 | 소~중규모 | ✅ 대규모 |
| 설치 | ❌ 불필요 | 필요 |
| 관리 | ❌ 쉬움 | 중간 |
| 원격 접속 | ❌ 불가 | ✅ 가능 |
| 백업 | 파일 복사 | pg_dump |

---

## 🎉 완료!

PostgreSQL 설정이 완료되었습니다.

문의사항: Ruby에게 연락하세요.
