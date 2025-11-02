# Monitoring API 통합 완료

**날짜**: 2025-10-31
**목적**: 하이브리드 Auto-labeling 시스템의 실시간 모니터링 API 통합

---

## 1. 통합 개요

Advanced Improvements로 구현된 모니터링 API를 FastAPI 메인 서버에 성공적으로 통합했습니다.

### 통합된 파일
- `backend/src/api/monitoring_api.py` ✅ 생성 완료
- `backend/src/utils/evaluation_analyzer.py` ✅ 생성 완료
- `backend/api_server.py` ✅ 라우터 등록 완료

---

## 2. API 엔드포인트

### 2.1 평가 통계 조회
```bash
GET /api/monitoring/labeling-stats?days=7
```

**응답 예시**:
```json
{
  "total_evaluations": 1250,
  "avg_quality_score": 0.84,
  "success_rate": 92.5,
  "cache_hit_rate": 28.4,
  "estimated_cost": "$8.95",
  "cost_per_evaluation": "$0.00006",
  "agent_stats": {
    "Router": {
      "count": 450,
      "avg_score": 0.87,
      "success_rate": 94.2
    },
    "Parent": {
      "count": 400,
      "avg_score": 0.82,
      "success_rate": 91.5
    },
    "Children": {
      "count": 400,
      "avg_score": 0.83,
      "success_rate": 91.8
    }
  }
}
```

### 2.2 A/B 테스트 결과 조회
```bash
GET /api/monitoring/ab-test-results?days=7
```

**응답 예시**:
```json
{
  "total_tests": 125,
  "hybrid_better_count": 98,
  "avg_rule_score": 0.72,
  "avg_hybrid_score": 0.84,
  "avg_score_difference": 0.12,
  "recommendation": "하이브리드 평가가 Rule-based보다 우수합니다. 전체 활성화를 권장합니다."
}
```

### 2.3 피드백 분석 (낮은 점수 패턴)
```bash
GET /api/monitoring/feedback-analysis?days=7
```

**응답 예시**:
```json
{
  "low_score_count": 45,
  "common_issues": [
    {
      "type": "맥락 이탈",
      "count": 18,
      "examples": [
        {
          "agent": "Router",
          "reason": "갑작스러운 주제 전환 감지 실패",
          "count": 8
        }
      ]
    },
    {
      "type": "캐릭터 톤 불일치",
      "count": 15,
      "examples": [
        {
          "agent": "Children",
          "reason": "친밀도 반영 미흡",
          "count": 10
        }
      ]
    }
  ],
  "recommendations": [
    "프롬프트에 '갑작스러운 주제 전환은 off_topic' 명시 강화",
    "캐릭터별 말투 예시를 프롬프트에 추가"
  ]
}
```

### 2.4 캐시 통계 조회
```bash
GET /api/monitoring/cache-stats
```

**응답 예시**:
```json
{
  "cache_size": 342,
  "cache_ttl": 3600,
  "cache_enabled": true
}
```

---

## 3. 통합 코드 변경사항

### 3.1 api_server.py 수정

**Import 추가** (Line 59-62):
```python
# ------------------------------------------------------------
# ✅ Monitoring API 로드
# ------------------------------------------------------------
from src.api.monitoring_api import router as monitoring_router
```

**Router 등록** (Line 91-94):
```python
# ------------------------------------------------------------
# ✅ API 라우터 등록
# ------------------------------------------------------------
app.include_router(monitoring_router)
```

### 3.2 버그 수정

**monitoring_api.py** (Line 13):
- 수정 전: `from typing import Dict, List, Optional`
- 수정 후: `from typing import Any, Dict, List, Optional` ✅

**monitoring_api.py** (Line 50):
- 수정 전: `common_issues: List[Dict[str, any]]`
- 수정 후: `common_issues: List[Dict[str, Any]]` ✅

**evaluation_analyzer.py** (Line 9):
- 수정 전: `from typing import Dict, List`
- 수정 후: `from typing import Dict, List, Optional` ✅

---

## 4. 사용 방법

### 4.1 서버 시작
```bash
cd /Users/jtm427/Desktop/workspace/backend
/Users/jtm427/miniconda3/envs/openai/bin/python api_server.py
```

### 4.2 API 테스트

**curl로 테스트**:
```bash
# 평가 통계 조회
curl http://localhost:8000/api/monitoring/labeling-stats?days=7

# A/B 테스트 결과
curl http://localhost:8000/api/monitoring/ab-test-results?days=7

# 피드백 분석
curl http://localhost:8000/api/monitoring/feedback-analysis?days=7

# 캐시 통계
curl http://localhost:8000/api/monitoring/cache-stats
```

**프론트엔드 통합 예시** (React):
```typescript
// src/utils/monitoringClient.ts
import apiClient from './apiClient';

export const monitoringApi = {
  // 평가 통계 조회
  getLabelingStats: async (days: number = 7) => {
    const response = await apiClient.get(`/api/monitoring/labeling-stats?days=${days}`);
    return response.data;
  },

  // A/B 테스트 결과
  getABTestResults: async (days: number = 7) => {
    const response = await apiClient.get(`/api/monitoring/ab-test-results?days=${days}`);
    return response.data;
  },

  // 피드백 분석
  getFeedbackAnalysis: async (days: number = 7) => {
    const response = await apiClient.get(`/api/monitoring/feedback-analysis?days=${days}`);
    return response.data;
  },

  // 캐시 통계
  getCacheStats: async () => {
    const response = await apiClient.get('/api/monitoring/cache-stats');
    return response.data;
  }
};
```

### 4.3 대시보드 컴포넌트 예시
```typescript
import React, { useEffect, useState } from 'react';
import { monitoringApi } from '../utils/monitoringClient';

export const MonitoringDashboard: React.FC = () => {
  const [stats, setStats] = useState(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    const fetchStats = async () => {
      const data = await monitoringApi.getLabelingStats(days);
      setStats(data);
    };
    fetchStats();
  }, [days]);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="monitoring-dashboard">
      <h1>Auto-labeling 모니터링</h1>

      <div className="period-selector">
        <button onClick={() => setDays(7)}>7일</button>
        <button onClick={() => setDays(14)}>14일</button>
        <button onClick={() => setDays(30)}>30일</button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>전체 평가</h3>
          <p className="value">{stats.total_evaluations.toLocaleString()}</p>
        </div>

        <div className="stat-card">
          <h3>평균 품질 점수</h3>
          <p className="value">{(stats.avg_quality_score * 100).toFixed(1)}%</p>
        </div>

        <div className="stat-card">
          <h3>성공률</h3>
          <p className="value">{stats.success_rate.toFixed(1)}%</p>
        </div>

        <div className="stat-card">
          <h3>캐시 히트율</h3>
          <p className="value">{stats.cache_hit_rate.toFixed(1)}%</p>
        </div>

        <div className="stat-card">
          <h3>예상 비용</h3>
          <p className="value">{stats.estimated_cost}</p>
          <p className="sub">({stats.cost_per_evaluation}/건)</p>
        </div>
      </div>

      <div className="agent-stats">
        <h2>에이전트별 통계</h2>
        {Object.entries(stats.agent_stats).map(([agent, agentStats]) => (
          <div key={agent} className="agent-card">
            <h3>{agent}</h3>
            <p>평가 수: {agentStats.count}</p>
            <p>평균 점수: {(agentStats.avg_score * 100).toFixed(1)}%</p>
            <p>성공률: {agentStats.success_rate.toFixed(1)}%</p>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 5. 환경변수 설정

### 5.1 .env 설정 확인
```bash
# Phase 4.5: LLM-based Auto-labeling (맥락 중심 하이브리드)
LLM_LABELING_ENABLED=true
LLM_LABELING_MODEL=gpt-4o-mini

# Phase 4.6: A/B Testing (선택사항)
AB_TEST_ENABLED=false
AB_TEST_RATIO=0.1  # 10%만 하이브리드 평가
```

### 5.2 A/B 테스트 활성화하기
A/B 테스트를 활성화하려면:
```bash
AB_TEST_ENABLED=true
```

이렇게 설정하면 `AB_TEST_RATIO`에 설정된 비율만큼 Rule-based와 Hybrid 평가를 동시에 수행하여 비교 데이터를 수집합니다.

---

## 6. 데이터베이스 테이블

### 6.1 A/B 테스트 테이블 (자동 생성)
`training_logger.py`가 A/B 테스트 모드일 때 자동으로 생성됩니다:

```sql
CREATE TABLE IF NOT EXISTS ab_test_results (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    turn_count INTEGER,
    agent_name TEXT,
    rule_score FLOAT,
    hybrid_score FLOAT,
    score_difference FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2 기존 테이블 활용
- `training_logs`: 전체 평가 데이터 저장 (outcome, feedback_score, outcome_reason)
- 캐시 히트 판단: `outcome_reason`에 "(cached)" 포함 여부

---

## 7. 검증 완료 사항

### 7.1 Import 검증
```bash
✅ Monitoring API import successful
✅ Evaluation Analyzer import successful
```

### 7.2 라우터 등록 검증
```bash
✅ Monitoring API routes successfully registered:
   - /api/monitoring/labeling-stats
   - /api/monitoring/ab-test-results
   - /api/monitoring/feedback-analysis
   - /api/monitoring/cache-stats

Total monitoring routes: 4
```

### 7.3 타입 오류 수정 완료
- `any` → `Any` 수정 ✅
- `Optional` import 추가 ✅

---

## 8. 다음 단계 (선택사항)

### 8.1 프론트엔드 대시보드 구현
- React 컴포넌트로 실시간 모니터링 페이지 구현
- Chart.js 또는 Recharts로 시각화
- 주기적 폴링 (예: 30초마다 자동 갱신)

### 8.2 알림 시스템
```python
# evaluation_analyzer.py에 추가
def send_alert_if_needed(self, analysis: Dict):
    """낮은 점수가 임계값을 초과하면 알림"""
    if analysis["total_low_scores"] > 50:
        # Slack/Discord webhook으로 알림 전송
        send_webhook_notification(
            f"⚠️ 낮은 점수 건수가 {analysis['total_low_scores']}건입니다!"
        )
```

### 8.3 자동 프롬프트 개선
```python
# 피드백 루프 자동화
def auto_improve_prompts(self):
    """낮은 점수 패턴을 분석하여 프롬프트 자동 개선"""
    suggestions = self.get_improvement_suggestions()

    # 프롬프트 파일에 자동으로 제안사항 추가
    with open("prompts_improvement_suggestions.md", "w") as f:
        f.write("\n".join(suggestions))
```

### 8.4 성능 메트릭 추가
- 응답 시간 (latency) 추적
- LLM API 호출 횟수/비용 상세 분석
- 에이전트별 평균 응답 시간

---

## 9. 문제 해결

### 9.1 "A/B test not enabled" 오류
**원인**: A/B 테스트 테이블이 생성되지 않음
**해결**: `.env`에서 `AB_TEST_ENABLED=true` 설정 후 서버 재시작

### 9.2 "No data found" 오류
**원인**: 해당 기간에 평가 데이터가 없음
**해결**:
1. 대화 테스트를 수행하여 평가 데이터 생성
2. 또는 `days` 파라미터를 더 크게 설정 (예: 30일)

### 9.3 캐시가 작동하지 않음
**확인 사항**:
```python
# training_logger.py에서 확인
print(f"Cache size: {len(self.evaluation_cache)}")
print(f"TTL: {self.cache_ttl}")
```

---

## 10. 요약

### 구현 완료 항목
- ✅ Monitoring API 4개 엔드포인트 구현
- ✅ Evaluation Analyzer 피드백 루프 구현
- ✅ FastAPI 메인 서버에 라우터 통합
- ✅ Import 오류 수정 (Any, Optional)
- ✅ 라우터 등록 검증

### 시스템 구성
```
Backend
├── api_server.py               # Monitoring Router 등록 ✅
├── src/
│   ├── api/
│   │   └── monitoring_api.py   # 4개 API 엔드포인트 ✅
│   ├── utils/
│   │   └── evaluation_analyzer.py  # 피드백 분석 ✅
│   └── tools/
│       └── training_logger.py  # 하이브리드 평가 + 캐시 + A/B 테스트 ✅
└── .env                        # LLM_LABELING_ENABLED, AB_TEST_ENABLED
```

### 다음 추천 작업
1. **프론트엔드 대시보드**: 실시간 모니터링 UI 구현
2. **A/B 테스트 활성화**: Rule vs Hybrid 성능 비교 데이터 수집
3. **알림 시스템**: 품질 저하 시 자동 알림
4. **자동 개선**: 피드백 루프 기반 프롬프트 자동 개선

---

**문서 작성**: 2025-10-31
**작성자**: Claude (AI Assistant)
**관련 문서**:
- [26_hybrid_autolabeling_implementation.md](./26_hybrid_autolabeling_implementation.md)
- [27_advanced_improvements_implementation.md](./27_advanced_improvements_implementation.md)
