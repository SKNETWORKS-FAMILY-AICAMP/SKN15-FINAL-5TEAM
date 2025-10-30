# KIME Chat 프로젝트 학습 기록

이 폴더는 KIME Chat 프로젝트의 개발 과정과 주요 기술 결정사항을 기록한 학습 자료입니다.

## 📁 문서 구조

### 01_database_setup.md
PostgreSQL과 Redis를 사용한 로컬 데이터베이스 구축 과정을 상세히 기록했습니다.
- Docker Compose를 이용한 컨테이너 구성
- StateDB와 LogDB 스키마 설계
- 하이브리드 세션 관리 시스템 구현

### 02_image_cdn_migration.md
로컬 이미지 경로를 AWS S3+CloudFront CDN으로 마이그레이션한 과정입니다.
- 하드코딩된 이미지 경로 문제 발견
- 환경 변수 기반 CDN URL 설정
- 9개 파일 43개 이미지 경로 수정 상세 내역

### 03_aws_deployment_guide.md
AWS 5-서버 아키텍처 배포 가이드입니다.
- 프론트엔드 2대 + 백엔드 2대 + RDS + ElastiCache + S3+CloudFront
- 예산 ₩300,000 내에서 27일간 운영하는 비용 최적화 전략
- 12시간 배포 타임라인

### 04_environment_variables.md
환경 변수 설정 및 관리 방법입니다.
- 로컬 개발 환경 (.env)
- AWS 프로덕션 환경 (.env.production)
- Vite 환경 변수 TypeScript 타입 정의

### 05_troubleshooting.md
개발 중 발생한 에러와 해결 방법을 정리했습니다.
- PostgreSQL 포트 충돌 해결
- Foreign Key 제약 조건 위반 해결
- TypeScript import.meta.env 타입 에러 해결

### 06_local_test_and_verification.md
로컬 환경에서 전체 시스템 테스트 과정입니다.
- 데이터베이스 연결 검증
- API 서버 통합 테스트
- 세션 관리 시스템 검증

### 07_code_review_and_architecture.md
전체 아키텍처 리뷰 및 코드 분석입니다.
- Multi-Agent 시스템 구조
- Router → Parent → Children → Dialogue 워크플로우
- 각 Agent의 역할과 책임

### 08_performance_optimization.md
초기 성능 최적화 작업입니다.
- LLM 모델 선택 전략
- 프롬프트 최적화 기법
- 캐싱 전략

### 09_phase1_image_manager_optimization.md
Image Manager 최적화 작업입니다.
- 이미지 선택 로직 개선
- 캐릭터 매칭 정확도 향상
- 스포일러 방지 메커니즘

### 10_aws_deployment_step_by_step.md
AWS 배포를 위한 단계별 가이드입니다.
- EC2 인스턴스 설정
- RDS 데이터베이스 구성
- CloudFront 배포
- 보안 그룹 설정

### 11_aws_security_guide.md
AWS 보안 설정 및 베스트 프랙티스입니다.
- IAM 정책 설정
- 보안 그룹 규칙
- SSL/TLS 인증서 관리

### 12_phase4_training_logs.md
Phase 4 Training Log 시스템 구현입니다.
- LogDB 설계 및 구축
- Auto-labeling 휴리스틱
- Fine-tuning 데이터 수집 전략

### 13_system_optimization_and_logging_complete.md
**[최신]** 전체 시스템 최적화 및 로깅 완성입니다.
- 성능 82% 향상 (25초 → 4-5초)
- 모든 Agent 로깅 시스템 완성
- 프롬프트 표준화 (200-400 토큰)
- 비용 98.5% 절감 (gpt-4-turbo → gpt-4o-mini)

## 🎯 학습 목표

이 문서들을 통해 다음을 학습할 수 있습니다:
1. 실전 데이터베이스 설계 및 구축
2. 클라우드 인프라 아키텍처 설계
3. 환경별 설정 관리 (개발/프로덕션)
4. 문제 해결 과정과 디버깅 방법
5. Multi-Agent 시스템 설계 및 구현
6. LLM 기반 시스템 성능 최적화
7. 프롬프트 엔지니어링 실전 기법
8. AI 학습 데이터 수집 및 파인튜닝 전략

## 📚 읽는 순서

### 기초 과정 (1-5번)
1. **01_database_setup.md** - 데이터베이스 기초부터 시작
2. **04_environment_variables.md** - 환경 변수 개념 이해
3. **02_image_cdn_migration.md** - 실전 리팩토링 경험
4. **03_aws_deployment_guide.md** - AWS 배포 전체 프로세스
5. **05_troubleshooting.md** - 실전 에러 대응법

### 심화 과정 (6-9번)
6. **06_local_test_and_verification.md** - 통합 테스트 방법
7. **07_code_review_and_architecture.md** - Multi-Agent 아키텍처 이해
8. **08_performance_optimization.md** - 성능 최적화 기초
9. **09_phase1_image_manager_optimization.md** - 실전 최적화 사례

### 고급 과정 (10-13번)
10. **10_aws_deployment_step_by_step.md** - AWS 단계별 배포
11. **11_aws_security_guide.md** - AWS 보안 베스트 프랙티스
12. **12_phase4_training_logs.md** - AI 학습 데이터 수집 시스템
13. **13_system_optimization_and_logging_complete.md** - 전체 시스템 최적화

## ⏱ 프로젝트 타임라인

### Phase 1: 인프라 구축
- **데이터베이스 구축**: 2025-10-30 (로컬 완료)
- **CDN 마이그레이션**: 2025-10-30 (완료)

### Phase 2: 아키텍처 리뷰
- **코드 리뷰 및 분석**: 2025-10-30 (완료)
- **Multi-Agent 시스템 이해**: 2025-10-30 (완료)

### Phase 3: 성능 최적화
- **초기 최적화**: 2025-10-30 (완료)
- **Image Manager 개선**: 2025-10-30 (완료)

### Phase 4: 학습 시스템
- **Training Log 구축**: 2025-10-30 (완료)
- **Auto-labeling 구현**: 2025-10-30 (완료)

### Phase 5: 시스템 완성
- **전체 최적화**: 2025-10-30 (완료)
  - 성능 82% 향상
  - 비용 98.5% 절감
  - 모든 Agent 로깅 완성
  - 프롬프트 표준화

### 다음 단계
- **AWS 배포**: 2025-10-31 예정 (12시간 소요 예상)
- **서비스 운영**: 27일 예정
- **데이터 수집**: 100개 이상 로그 목표
- **파인튜닝**: 1-2주 후 시작 예정

---
최종 업데이트: 2025-10-30
작성자: Claude (AI Assistant)
프로젝트: KIME Chat - 귀멸의 칼날 멀티 에이전트 대화 시스템
