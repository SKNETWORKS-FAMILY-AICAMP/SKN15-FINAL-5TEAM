# 🚀 빠른 시작 가이드

## 조원들을 위한 한 줄 실행 가이드

```bash
docker-compose up
```

**끝!** 이것만 실행하면 모든 설정이 자동으로 완료됩니다.

## 📋 자동으로 실행되는 작업들

1. ✅ PostgreSQL 데이터베이스 준비 대기
2. ✅ Alembic 마이그레이션 자동 실행
3. ✅ 초기 시나리오 데이터 자동 임포트 (scenarios 테이블이 비어있는 경우)
4. ✅ 모든 사용자에게 초기 200 버블 크레딧 자동 지급
5. ✅ 백엔드 서버 시작 (http://localhost:8000)
6. ✅ 프론트엔드 서버 시작 (http://localhost)

## 🌐 접속 URL

- **프론트엔드**: http://localhost
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 🔑 테스트 계정

이미 생성된 테스트 계정들 (각각 200 버블 보유):
- `tanjiro` / 비밀번호는 `create_test_users.py` 참고
- `zenitsu` / 비밀번호는 `create_test_users.py` 참고
- `inosuke` / 비밀번호는 `create_test_users.py` 참고

또는 새로 회원가입하면 자동으로 200 버블이 지급됩니다!

## 🛠 문제 해결

### 포트가 이미 사용 중인 경우
```bash
# 80번 포트를 사용 중인 프로세스 확인
lsof -i :80

# 8000번 포트를 사용 중인 프로세스 확인
lsof -i :8000

# 5432번 포트를 사용 중인 프로세스 확인 (PostgreSQL)
lsof -i :5432
```

### 컨테이너 재시작
```bash
# 모든 컨테이너 재시작
docker-compose restart

# 특정 컨테이너만 재시작
docker-compose restart backend
```

### 완전히 새로 시작 (DB 데이터 초기화)
```bash
# 모든 컨테이너와 볼륨 삭제
docker-compose down -v

# 다시 시작
docker-compose up
```

### 로그 확인
```bash
# 모든 서비스 로그
docker-compose logs

# 백엔드만
docker-compose logs backend

# 실시간 로그 (tail -f)
docker-compose logs -f backend
```

## ✨ 주요 기능

### 1. 친밀도 시스템
- 대화할 때마다 캐릭터별 친밀도가 누적됩니다
- 친밀도는 DB에 저장되어 세션 간 유지됩니다
- 프론트엔드 오른쪽에 실시간으로 표시됩니다

### 2. 버블 크레딧 시스템
- 신규 가입 시 200 버블 자동 지급
- 대화할 때마다 버블 소비
- 헤더에 남은 버블 개수 표시

### 3. XP 및 레벨 시스템
- 대화, 시나리오 완료 등으로 XP 획득
- 일정 XP 도달 시 자동 레벨업

## 📝 환경 변수 (.env)

`.env` 파일이 없다면 `.env.example`을 복사하여 사용하세요:

```bash
cp .env.example .env
```

필수 설정:
- `OPENAI_API_KEY`: OpenAI API 키 (필수)
- `DB_PASSWORD`: PostgreSQL 비밀번호 (기본값: dev123)

## 🔄 Git 작업 시 주의사항

```bash
# 최신 코드 가져오기
git pull origin tm-merge-all-logic

# Docker 재시작 (마이그레이션 자동 실행됨)
docker-compose restart backend
```

## 📚 더 자세한 정보

- [TEAM_SETUP_GUIDE.md](./TEAM_SETUP_GUIDE.md) - 상세한 팀 설정 가이드
- [backend/README.md](./backend/README.md) - 백엔드 아키텍처 설명
- [front/README.md](./front/README.md) - 프론트엔드 구조 설명

## 🆘 도움이 필요하면

1. Docker 로그 확인: `docker-compose logs backend --tail=50`
2. DB 접속 확인: `docker-compose exec postgres psql -U kime -d kimedb`
3. 백엔드 컨테이너 접속: `docker-compose exec backend bash`

문제가 해결되지 않으면 팀 채팅방에 로그와 함께 문의해주세요!
