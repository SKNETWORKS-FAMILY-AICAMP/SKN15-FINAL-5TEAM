# Git Push 체크리스트

Git에 푸시하기 전에 다음 항목들을 확인하세요.

---

## 1. 보안 체크 ⚠️

### 1.1 환경변수 및 시크릿
- [ ] `.env` 파일이 Git에 커밋되지 않았는지 확인
  ```bash
  git status | grep ".env$"
  # 아무것도 출력되지 않아야 함
  ```
- [ ] `.env.example`에 실제 값이 아닌 예시 값만 있는지 확인
- [ ] 코드에 하드코딩된 API 키가 없는지 검색
  ```bash
  grep -r "sk-" backend/ front/ --exclude-dir=node_modules
  grep -r "OPENAI_API_KEY.*=" backend/ front/ --exclude-dir=node_modules
  ```
- [ ] JWT 시크릿이 코드에 포함되지 않았는지 확인
  ```bash
  grep -r "JWT_SECRET" backend/ --exclude-dir=__pycache__
  ```

### 1.2 데이터베이스 크레덴셜
- [ ] PostgreSQL 비밀번호가 코드에 없는지 확인
- [ ] Redis 비밀번호가 코드에 없는지 확인
- [ ] `docker-compose.yml`에 프로덕션 비밀번호가 없는지 확인 (개발용만)

---

## 2. .gitignore 확인

### 2.1 필수 제외 항목
- [ ] `.env` (환경변수)
- [ ] `__pycache__/` (Python 캐시)
- [ ] `*.pyc` (Python 컴파일 파일)
- [ ] `node_modules/` (Node 패키지)
- [ ] `dist/`, `build/` (빌드 산출물)
- [ ] `.DS_Store` (macOS 메타데이터)
- [ ] `*.log` (로그 파일)
- [ ] `backups/*.sql` (데이터베이스 백업)
- [ ] `.vscode/`, `.idea/` (IDE 설정 - 선택)

### 2.2 확인 명령어
```bash
# .gitignore에 포함되어야 할 파일들이 git에 추적되는지 확인
git status --ignored
```

---

## 3. 코드 품질 체크

### 3.1 마이그레이션
- [ ] 모든 마이그레이션 파일이 커밋되었는지 확인
  ```bash
  ls backend/database/migrations/
  ```
- [ ] 마이그레이션 파일 번호가 순차적인지 확인 (001, 002, ... 019)
- [ ] 최신 마이그레이션 파일이 정상 실행되는지 테스트
  ```bash
  cat backend/database/migrations/019_scenario_comments.sql | \
    docker-compose exec -T postgres psql -U kime -d kimedb
  ```

### 3.2 기능 테스트
- [ ] 로그인/로그아웃이 정상 동작하는지 확인
- [ ] 시나리오 목록 페이지가 로드되는지 확인
- [ ] 시나리오 상세 페이지가 로드되는지 확인
- [ ] 댓글 작성이 정상 동작하는지 확인
- [ ] 댓글 좋아요가 정상 동작하는지 확인
- [ ] 시나리오 좋아요가 정상 동작하는지 확인

### 3.3 Docker 빌드
- [ ] Docker 컨테이너가 정상 빌드되는지 확인
  ```bash
  docker-compose down
  docker-compose up -d --build
  ```
- [ ] 모든 컨테이너가 정상 실행되는지 확인
  ```bash
  docker-compose ps
  # 모든 서비스가 "Up" 상태여야 함
  ```
- [ ] 헬스체크가 통과하는지 확인
  ```bash
  docker-compose ps | grep healthy
  ```

---

## 4. 문서 확인

### 4.1 필수 문서
- [ ] `README.md` 존재 및 최신 상태 확인
- [ ] `SETUP.md` 존재 및 정확한 설명 확인
- [ ] `.env.example` 존재 및 모든 필수 변수 포함 확인
- [ ] `GIT_PUSH_CHECKLIST.md` (이 파일) 포함 확인

### 4.2 문서 내용
- [ ] README에 프로젝트 설명 포함
- [ ] SETUP에 팀원 온보딩 절차 포함
- [ ] 환경변수 설명이 명확한지 확인
- [ ] 스크립트 사용법이 문서화되었는지 확인

---

## 5. 커밋 메시지

### 5.1 커밋 컨벤션
현재 작업의 주요 변경사항:
- feat: 시나리오 댓글 시스템 추가
- feat: 댓글 좋아요 기능 추가
- feat: 시나리오 좋아요 기능 추가
- docs: 팀 온보딩 문서 추가
- chore: 데이터베이스 백업/복원 스크립트 추가

### 5.2 커밋 전 확인
```bash
# 변경된 파일 확인
git status

# 변경 내용 확인
git diff

# 스테이징된 파일 확인
git diff --staged
```

### 5.3 권장 커밋 메시지
```bash
git commit -m "feat: Add scenario comment system with likes

- Add comment CRUD endpoints (create, read, update, delete)
- Add comment like/unlike functionality
- Add scenario like/unlike functionality
- Support comment sorting (recent/popular)
- Add comment reply support (1-level nested)
- Add PostgreSQL migration for comments (019)
- Add CommentsMixin to db_manager
- Add comment UI to CharacterPage
- Add team setup documentation and scripts

Database changes:
- scenario_comments table with soft delete
- comment_likes table for user-comment relationships
- Auto-update triggers for counts
- SQL functions for comment retrieval with sorting

Refs: #issue-number"
```

---

## 6. 브랜치 전략

### 6.1 현재 브랜치 확인
```bash
git branch
# 현재: main 브랜치
```

### 6.2 브랜치 전략 (권장)
- `main`: 프로덕션 배포 브랜치
- `develop`: 개발 통합 브랜치
- `feature/*`: 기능 개발 브랜치

### 6.3 브랜치 생성 (선택)
현재는 main에 바로 푸시하지만, 팀 협업 시 브랜치 전략 고려:
```bash
# 기능 브랜치 생성
git checkout -b feature/comment-system

# 작업 후 커밋
git add .
git commit -m "feat: Add comment system"

# 원격에 푸시
git push origin feature/comment-system

# Pull Request 생성 후 리뷰
```

---

## 7. 푸시 전 최종 확인

### 7.1 로컬 테스트
- [ ] 로컬에서 모든 기능이 정상 동작
- [ ] Docker Compose로 clean build 성공
  ```bash
  docker-compose down -v
  docker-compose up -d --build
  ```
- [ ] 브라우저에서 모든 페이지 접속 확인
  - [ ] http://localhost (홈페이지)
  - [ ] http://localhost/character/mugen_train_full (상세 페이지)
  - [ ] http://localhost:8000/docs (API 문서)

### 7.2 데이터 백업
- [ ] 중요한 데이터가 있다면 백업
  ```bash
  ./scripts/backup_database.sh important_backup.sql
  ```

### 7.3 팀원 공유용 백업 생성 (선택)
- [ ] 샘플 데이터 백업 생성
  ```bash
  ./scripts/backup_database.sh sample_data.sql
  ```
- [ ] `backups/` 폴더를 Git에서 제외했는지 확인

---

## 8. 푸시 실행

### 8.1 변경사항 스테이징
```bash
# 모든 변경사항 추가
git add .

# 또는 선택적 추가
git add backend/database/migrations/019_scenario_comments.sql
git add backend/src/database/db_manager_comments.py
git add backend/src/api/scenario_router.py
git add front/src/pages/CharacterPage.tsx
git add front/src/services/api.ts
git add SETUP.md
git add GIT_PUSH_CHECKLIST.md
git add scripts/
```

### 8.2 커밋
```bash
git commit -m "feat: Add scenario comment system with likes

- Add comment CRUD endpoints
- Add comment like functionality
- Add scenario like functionality
- Support comment sorting (recent/popular)
- Add team setup documentation

Database: Add 019_scenario_comments.sql migration"
```

### 8.3 푸시
```bash
# main 브랜치에 푸시
git push origin main

# 또는 feature 브랜치에 푸시
git push origin feature/comment-system
```

---

## 9. 푸시 후 확인

### 9.1 원격 저장소 확인
- [ ] GitHub/GitLab에서 커밋이 정상 반영되었는지 확인
- [ ] CI/CD 파이프라인이 있다면 성공했는지 확인
- [ ] Actions/Workflows가 실패하지 않았는지 확인

### 9.2 팀원에게 공지
Slack/Discord 등에 공지 메시지:

```
📢 새로운 기능이 추가되었습니다!

✨  주요 변경사항:
- 시나리오 상세 페이지에 댓글 시스템 추가
- 댓글/시나리오 좋아요 기능 추가
- 댓글 최신순/인기순 정렬 지원

🔧 업데이트 방법:
1. git pull origin main
2. docker-compose down
3. docker-compose up -d --build
4. (선택) 샘플 데이터 복원: ./scripts/restore_database.sh backups/sample_data.sql

📚 문서:
- 팀 설정 가이드: SETUP.md
- Git 푸시 체크리스트: GIT_PUSH_CHECKLIST.md

❓ 문제 발생 시:
- SETUP.md의 "문제 해결" 섹션 참고
- 또는 팀 채널에 문의
```

---

## 10. 트러블슈팅

### 문제: Git이 .env 파일을 추적하고 있음
```bash
# .env 파일을 Git 추적에서 제거 (파일은 유지)
git rm --cached .env

# 커밋
git commit -m "chore: Remove .env from git tracking"
```

### 문제: 실수로 API 키를 커밋함
```bash
# 최근 커밋 취소 (아직 푸시 전)
git reset --soft HEAD~1

# API 키 제거 후 다시 커밋
# 파일 수정...
git add .
git commit -m "fix: Remove API keys"
```

**⚠️ 이미 푸시했다면**: API 키를 즉시 재발급하고 Git 히스토리 재작성 필요 (위험)

### 문제: 너무 많은 파일이 스테이징됨
```bash
# 스테이징 취소
git reset

# 필요한 파일만 선택적으로 추가
git add backend/database/migrations/019_scenario_comments.sql
# ...
```

---

## ✅ 최종 체크리스트

푸시 전에 다음을 모두 확인했는지 체크:

- [ ] 보안: API 키, 시크릿이 코드에 없음
- [ ] .gitignore: 민감한 파일들이 제외됨
- [ ] 마이그레이션: 모든 SQL 파일이 커밋되고 테스트됨
- [ ] Docker: 클린 빌드가 성공함
- [ ] 기능 테스트: 모든 주요 기능이 동작함
- [ ] 문서: SETUP.md, .env.example이 최신 상태
- [ ] 커밋 메시지: 명확하고 상세함
- [ ] 로컬 테스트: 전체 워크플로우 확인

**모두 체크했다면 푸시하세요! 🚀**

```bash
git push origin main
```
