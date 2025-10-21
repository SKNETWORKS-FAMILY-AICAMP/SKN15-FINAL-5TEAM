# 📋 Git 포함/제외 파일 요약

## ✅ Git에 포함되는 파일 (팀원들과 공유)

### 📖 문서
- README.md
- QUICK_START.md ⭐ NEW
- GIT_SETUP_GUIDE.md ⭐ NEW
- DELIVERABLES.md
- IMPLEMENTATION_COMPLETE.md
- JSON_SCHEMA_DIAGRAM.md
- README_TESTING.md
- SCENARIO_IMPLEMENTATION_PLAN.md
- SYSTEM_ANALYSIS_AND_RECOMMENDATIONS.md
- TESTING_QUICK_START.md

### 🐍 실행 파일
- play.py (메인 실행 파일)
- main.py
- requirements.txt ⭐ 필수

### 🎯 소스 코드 (src/)
- src/agents/ (parent_agent.py, children_agent.py 등)
- src/core/ (workflow.py, graph_state.py 등)
- src/tools/
- src/utils/

### 📊 데이터 (data/)
- data/scenarios/ (시나리오 JSON 파일들)
- data/characters_db.json
- data/character_raw_data/
- data/conversation_prompts.json
- data/images_catalog.json
- data/scenes.json
- data/proactive_20_cases.json
- data/game_state.db

### ⚙️ 설정 (configs/)
- configs/settings.yaml
- configs/prompts.yaml
- configs/characters.yaml
- configs/routing_rules.json
- configs/parent_config.json

### 🧪 테스트 파일
- test_*.py (모든 테스트 파일)
- conftest.py
- tests/ 폴더
- RUN_TESTS.sh

### 🔑 예시 파일
- .env.example ⭐ NEW (환경 변수 예시)
- .gitignore ⭐ NEW

---

## ❌ Git에서 제외되는 파일 (공유 안 됨)

### 🔒 민감한 정보
- ✋ .env (실제 API 키 포함)
- ✋ .env.local
- ✋ *.key, *.pem
- ✋ credentials.json
- ✋ secrets/

### 🖥️ 개인 설정
- ✋ .claude/ (Claude Code 설정)
- ✋ .vscode/
- ✋ .idea/

### 🗑️ 캐시 및 임시 파일
- ✋ __pycache__/
- ✋ *.pyc, *.pyo
- ✋ .pytest_cache/
- ✋ .coverage
- ✋ logs/ (로그 파일들)
- ✋ temp/
- ✋ *.log, *.tmp, *.bak

### 📊 실험 데이터
- ✋ logs/experiments/
- ✋ logs/experiments_backup/
- ✋ logs/dev/
- ✋ manual_test_*.json

---

## 📏 크기 비교

| 항목 | 크기 | 포함 여부 |
|------|------|----------|
| 전체 프로젝트 | 5.5MB | - |
| logs/ | 1.1MB | ❌ 제외 |
| __pycache__/ | 800KB | ❌ 제외 |
| .pytest_cache/ | 56KB | ❌ 제외 |
| .coverage | 52KB | ❌ 제외 |
| .claude/ | 8KB | ❌ 제외 |
| .env | 227B | ❌ 제외 |
| **Git 포함 크기** | **약 3.5MB** | ✅ 공유 |

---

## 🔍 확인 방법

### Git에 포함될 파일 확인
\`\`\`bash
git add -n .
\`\`\`

### 제외된 파일 확인
\`\`\`bash
git status --ignored
\`\`\`

### 특정 파일이 제외되는지 확인
\`\`\`bash
git check-ignore -v .env
git check-ignore -v .claude/
\`\`\`

---

## ⚠️ 주의사항

1. **절대로 커밋하면 안 되는 것들:**
   - ❌ `.env` 파일 (API 키 포함)
   - ❌ `.claude/` 폴더 (개인 설정)
   - ❌ `credentials.json`, `*.key` 등

2. **반드시 포함해야 하는 것들:**
   - ✅ `.env.example` (환경 변수 예시)
   - ✅ `requirements.txt` (필수 패키지)
   - ✅ `.gitignore` (제외 규칙)

3. **실수로 민감한 파일을 커밋한 경우:**
   \`\`\`bash
   # 파일을 Git 히스토리에서 제거
   git rm --cached .env
   git commit -m "Remove .env from Git"
   
   # 이미 푸시한 경우 (주의: 팀원들에게 알려야 함)
   git push -f origin main
   \`\`\`

---

## 📝 체크리스트

커밋하기 전에 확인:

- [ ] `.env` 파일이 Git에 포함되지 않았는가?
- [ ] `.env.example` 파일은 포함되었는가?
- [ ] API 키나 비밀번호가 코드에 하드코딩되지 않았는가?
- [ ] 로그 파일이나 캐시가 제외되었는가?
- [ ] `requirements.txt`가 최신인가?

