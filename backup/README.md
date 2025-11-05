# Backup Directory

이 폴더에는 프로젝트 정리 과정에서 백업된 문서 및 파일들이 포함되어 있습니다.

## 📁 Directory Structure

```
backup/
├── docs/                       # 루트 레벨 문서들
│   ├── AWS_SECURITY_GROUP_SETUP.md
│   ├── DBEAVER_LOCAL_SETUP.md
│   ├── DOCKER_DEPLOYMENT_GUIDE.md
│   ├── TRAINING_DATA_ANALYSIS.md
│   └── documents/              # 기존 documents 폴더
│       ├── 10_aws_deployment_step_by_step.md
│       ├── 11_aws_security_guide.md
│       ├── 12_phase4_training_logs.md
│       └── 2025-10-30-database-and-aws-architecture-final.md
│
├── backend/                    # 백엔드 관련 백업
│   ├── RENGOKU_DISCIPLE_NARRATIVE.md
│   ├── OPEN_NARRATIVE_IMPLEMENTATION.md
│   ├── STAGE_TYPES_EXPLAINED.md
│   └── api_server.py.backup    # 리팩토링 전 원본 파일 (2,608줄)
│
└── frontend/                   # 프론트엔드 관련 백업
    ├── BACKGROUND_IMAGES_README.md
    ├── BACKEND_INTEGRATION_GUIDE.md
    └── MIGRATION_SUMMARY.md
```

## 📊 Statistics

- **총 백업 파일**: 14개
- **총 라인 수**: 약 5,755줄
- **백업 날짜**: 2025-11-05

## 📝 Backup Reason

### 1. 문서 정리
- AWS 배포 가이드, 보안 설정 등은 이미 완료된 작업
- 개발 단계별 로그는 참고용으로 보관
- 프로젝트 루트를 깔끔하게 유지

### 2. 코드 리팩토링
- `api_server.py.backup`: 리팩토링 전 원본 (92KB, 2,608줄)
- 새 구조: `api_server_new.py` (5.5KB, 169줄) + 12개 모듈

### 3. 개발 기록 보존
- 시나리오 설계 문서 (RENGOKU_DISCIPLE_NARRATIVE.md)
- 스테이지 타입 설명 (STAGE_TYPES_EXPLAINED.md)
- 마이그레이션 요약 (MIGRATION_SUMMARY.md)

## 🔍 Active Documentation

현재 프로젝트에서 유지되는 문서:
- **README.md** (루트): 프로젝트 전체 가이드
- **backend/demo_queries/README.md**: 데모 쿼리 설명
- **front/README.md**: 프론트엔드 설정 가이드

## ⚠️ Note

이 폴더의 파일들은 삭제하지 마세요. 프로젝트 히스토리 및 참고 자료로 보관됩니다.
