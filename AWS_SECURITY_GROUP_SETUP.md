# AWS 보안 그룹 설정 가이드 (DBeaver RDS 연결)

## 현재 화면 상태
보안 그룹 목록이 보입니다:
- `sg-026cf33eb09ac2fa4` - **kime-rds-sg** ← 이것을 선택해야 합니다!
- `sg-038e0f3ec7c87ae78` - kime-alb-sg

---

## 단계별 진행 방법

### Step 1: kime-rds-sg 선택 ✋ **지금 여기!**

**화면에서 할 일**:
1. **"kime-rds-sg"** 보안 그룹 이름을 **클릭**하세요
   - 또는 보안 그룹 ID `sg-026cf33eb09ac2fa4`를 클릭
2. 새 화면이 열립니다

---

### Step 2: 인바운드 규칙 탭으로 이동

**새 화면에서**:
1. 하단에 여러 탭이 보입니다:
   - Details (세부 정보)
   - **Inbound rules (인바운드 규칙)** ← 이 탭 클릭
   - Outbound rules (아웃바운드 규칙)
   - Tags (태그)

2. **"Inbound rules"** 탭을 클릭하세요

---

### Step 3: 인바운드 규칙 편집

**Inbound rules 탭에서**:
1. 우측 상단에 **"Edit inbound rules"** 버튼을 클릭
2. 새로운 편집 화면이 나타납니다

---

### Step 4: 새 규칙 추가

**Edit inbound rules 화면에서**:
1. 하단에 **"Add rule"** 버튼 클릭
2. 새 규칙 줄이 추가됩니다

**새 규칙 설정**:
```
Type:        PostgreSQL (드롭다운에서 선택)
Protocol:    TCP (자동 설정됨)
Port range:  5432 (자동 설정됨)
Source:      My IP (드롭다운에서 선택)
             → 자동으로 112.218.188.155/32 입력됨
Description: DBeaver access from local machine
```

**Type 선택 방법**:
- Type 드롭다운 클릭
- "PostgreSQL" 검색 또는 선택
- Port가 자동으로 5432로 설정됩니다

**Source 선택 방법**:
- Source 드롭다운 클릭
- **"My IP"** 선택
- 현재 IP (112.218.188.155/32)가 자동으로 입력됩니다

---

### Step 5: 규칙 저장

1. 우측 하단 **"Save rules"** 버튼 클릭
2. 성공 메시지 확인: "Successfully modified rules"

---

## 예상 화면 흐름

```
[현재 화면]
보안 그룹 목록
├── kime-rds-sg ← 클릭!
└── kime-alb-sg

↓ 클릭 후

[보안 그룹 상세 화면]
탭: Details | Inbound rules | Outbound rules | Tags
     ← "Inbound rules" 탭 클릭!

↓ 탭 클릭 후

[Inbound rules 화면]
Inbound rules (0개 또는 기존 규칙들)
우측 상단: [Edit inbound rules] ← 클릭!

↓ 버튼 클릭 후

[Edit inbound rules 화면]
기존 규칙들...
하단: [Add rule] ← 클릭!

↓ Add rule 후

[새 규칙 추가]
Type: [PostgreSQL ▼]
Protocol: TCP
Port range: 5432
Source: [My IP ▼] → 112.218.188.155/32
Description: [DBeaver access from local machine]

하단: [Cancel] [Save rules] ← Save rules 클릭!

↓ 저장 후

✅ Successfully modified rules
```

---

## 트러블슈팅

### "My IP" 옵션이 안 보여요
- Source 필드를 직접 입력하세요: `112.218.188.155/32`
- `/32`를 꼭 붙이세요 (단일 IP 의미)

### Type에서 PostgreSQL을 못 찾겠어요
- Type을 "Custom TCP"로 선택
- Port range에 수동으로 `5432` 입력

### 기존에 규칙이 있어요
- 기존 규칙을 확인하세요
- 이미 PostgreSQL 5432 포트가 0.0.0.0/0으로 열려있다면:
  - 이것은 **보안 위험**입니다
  - "Edit" 버튼으로 해당 규칙의 Source를 `112.218.188.155/32`로 변경하세요

---

## 설정 후 확인

### DBeaver에서 연결 테스트

```
Host:     kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
Port:     5432
Database: kimedb
Username: kime
Password: jnhzlsyihvxwfhvz
SSL mode: require
```

**Test Connection** 클릭 → ✅ "Connected" 확인!

### 터미널에서 연결 테스트

```bash
nc -zv kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com 5432
```

**성공 메시지**:
```
Connection to kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com port 5432 [tcp/postgresql] succeeded!
```

---

## 현재 내 IP
```
112.218.188.155
```

이 IP가 변경되면 (공유기 재시작, 다른 와이파이 사용 등) 보안 그룹을 다시 수정해야 합니다.

---

**다음 단계**: kime-rds-sg를 클릭하세요!
