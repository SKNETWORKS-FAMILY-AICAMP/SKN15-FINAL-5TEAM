# RDS Connection Timeout 해결 가이드

## 🚨 현재 문제

```
DBeaver 오류: Connection timeout
psql 오류:   Operation timed out
```

**원인**: RDS가 Private Subnet에 있어서 외부에서 직접 접근 불가

**현재 설정**:
- ✅ Public Access = Yes
- ✅ Security Group = 0.0.0.0/0 (Port 5432 열림)
- ❌ Subnet이 Private (Internet Gateway 없음)

---

## ✅ 해결 방법: RDS를 Public Subnet으로 변경

### AWS Console에서 확인 및 수정

#### Step 1: RDS Subnet Group 확인

1. **AWS Console** → **RDS**
2. 왼쪽 메뉴 → **Subnet groups**
3. RDS가 사용 중인 Subnet Group 클릭
4. **Subnets** 확인:
   - Private subnet인지 확인
   - Availability Zone 확인

#### Step 2: VPC 확인

1. **AWS Console** → **VPC**
2. **Subnets** 메뉴
3. RDS가 사용 중인 Subnet 찾기
4. **Route table** 확인:
   - `0.0.0.0/0 → igw-xxxxx` (Internet Gateway) 있어야 함
   - 없으면 Private Subnet

#### Step 3-A: Public Subnet Group 생성 (권장)

**1. Subnet Group 생성**:
1. RDS → **Subnet groups** → **Create DB subnet group**
2. 정보 입력:
   ```
   Name: kime-db-public-subnet-group
   Description: Public subnet group for RDS
   VPC: (현재 RDS와 동일한 VPC 선택)
   ```

3. **Add subnets**:
   - Availability Zones: ap-northeast-2a, ap-northeast-2c 선택
   - **Public Subnets만** 선택
   - Public Subnet 구분법:
     - Route table에 `0.0.0.0/0 → igw-xxxxx` 있음
     - 이름에 "public" 포함

4. **Create** 클릭

**2. RDS Subnet Group 변경**:
1. RDS → Databases → **kime-db**
2. **Modify** 클릭
3. **Network & Security** 섹션:
   ```
   Subnet group: kime-db-public-subnet-group
   Public access: Yes
   ```
4. **Continue** → **Apply immediately** → **Modify DB instance**

⏰ **재시작 시간**: 5-10분

---

#### Step 3-B: 기존 Subnet을 Public으로 변경 (복잡함)

**1. Internet Gateway 연결**:
1. VPC → **Internet Gateways**
2. **Create internet gateway** (없는 경우)
3. VPC에 Attach

**2. Route Table 수정**:
1. VPC → **Route Tables**
2. RDS Subnet의 Route Table 선택
3. **Routes** 탭 → **Edit routes**
4. **Add route**:
   ```
   Destination: 0.0.0.0/0
   Target:      Internet Gateway (igw-xxxxx)
   ```
5. **Save changes**

⏰ **적용 시간**: 즉시

---

## 🔍 Public Subnet 확인 방법

### VPC Console에서:
1. **VPC** → **Subnets**
2. Subnet 클릭
3. **Route table** 탭 확인
4. **Public Subnet 조건**:
   ```
   Destination     Target
   0.0.0.0/0       igw-xxxxxxxx    ← 이게 있어야 Public
   ```

---

## 🎯 설정 후 테스트

### 1. 터미널에서 연결 테스트
```bash
PGPASSWORD=jnhzlsyihvxwfhvz psql \
  -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 \
  -U kime \
  -d kimedb \
  -c "SELECT NOW();"
```

**성공 메시지**:
```
              now
-------------------------------
 2025-11-03 23:15:42.123456+00
(1 row)
```

### 2. DBeaver 연결
```
Host:     kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
Port:     5432
Database: kimedb
Username: kime
Password: jnhzlsyihvxwfhvz
```

**Test Connection** → ✅ Connected!

---

## 📊 체크리스트

RDS 외부 접근을 위한 필수 조건:

```
Network 설정:
- [ ] Public Access = Yes
- [ ] Security Group에 Port 5432 허용
- [ ] Subnet이 Public (Route table에 IGW 있음)
- [ ] VPC에 Internet Gateway 연결됨
- [ ] RDS가 Public Subnet Group 사용

연결 테스트:
- [ ] psql 터미널 연결 성공
- [ ] DBeaver Test Connection 성공
- [ ] 쿼리 실행 가능
```

---

## ⚠️ 보안 권장사항

RDS를 Public으로 만든 후:

### 1. Security Group 수정
```
현재: 0.0.0.0/0 (전 세계 허용) ← 위험!
권장: 112.218.188.155/32 (내 IP만) ← 안전
```

### 2. SSL 강제
```sql
-- PostgreSQL에서
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
```

### 3. 비밀번호 변경
```sql
ALTER USER kime WITH PASSWORD 'new_strong_password_123!@#';
```

---

## 🆘 여전히 안 되면?

### 최후의 방법: RDS 재생성

**1. 현재 RDS 스냅샷 생성**
2. **Public Subnet Group으로 새 RDS 생성**
3. **스냅샷에서 복원**

시간이 많이 걸리므로 마지막 수단입니다.

---

## 🎯 지금 확인할 것

AWS Console에서 확인해주세요:

### 1. RDS Subnet Group
- RDS → Subnet groups → (현재 사용 중인 그룹)
- Subnets의 Route table 확인

### 2. VPC Route Table
- VPC → Subnets → (RDS 사용 중인 subnet)
- Route table에 `0.0.0.0/0 → igw-xxxxx` 있나요?

**있음** → 이미 Public, 다른 문제
**없음** → Private Subnet, 위 Step 3 실행 필요

---

**작성일**: 2025-11-03
**목표**: RDS 외부 접근 가능하게 만들기
