# 스키마 불일치 수정 요약

## 문제 발견
- public.users 테이블이 auth.users와 중복 → **삭제 완료 ✅**
- 여러 모델에 `__table_args__ = {"schema": "xxx"}` 누락

## 수정 필요 파일

### 1. galleries/models.py (public 스키마)
```python
class GalleryImage(Base):
    __tablename__ = "gallery_images"
    __table_args__ = {"schema": "public"}  # 추가 필요

class GalleryImageLike(Base):
    __tablename__ = "gallery_image_likes"
    __table_args__ = (
        ...,
        {"schema": "public"}  # 추가 필요
    )

class GalleryImageView(Base):
    __tablename__ = "gallery_image_views"
    __table_args__ = (
        ...,
        {"schema": "public"}  # 추가 필요
    )
```

### 2. game/models.py
```python
class UserEquipment(Base):
    __tablename__ = "user_equipment"
    __table_args__ = {"schema": "progression"}  # 추가

class RankDefinition(Base):
    __tablename__ = "rank_definitions"
    __table_args__ = {"schema": "content"}  # 추가

class GameEvent(Base):
    __tablename__ = "game_events"
    __table_args__ = {"schema": "progression"}  # 추가

class MissionRecord(Base):
    __tablename__ = "mission_records"
    __table_args__ = {"schema": "progression"}  # 추가

class UserUnlockedImage(Base):
    __tablename__ = "user_unlocked_images"
    # 테이블 없음 - 생성 필요 또는 삭제 필요
```

### 3. logging/models.py
```python
class Log(Base):
    __tablename__ = "logs"
    __table_args__ = {"schema": "observability"}  # 추가

class ErrorLog(Base):
    __tablename__ = "error_logs"
    __table_args__ = {"schema": "observability"}  # 추가

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    __table_args__ = {"schema": "observability"}  # 추가

class TrainingLog(Base):
    __tablename__ = "training_logs"
    __table_args__ = {"schema": "ml"}  # 추가
```

### 4. misc/models.py
```python
class SessionSnapshot(Base):
    __tablename__ = "session_snapshots"
    __table_args__ = {"schema": "conversation"}  # 추가

class ScenarioStatistics(Base):
    __tablename__ = "scenario_statistics"
    __table_args__ = {"schema": "content"}  # 추가

class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = {"schema": "ml"}  # 추가
```

### 5. images/legacy_models.py
```python
# 이 파일은 legacy이므로 사용 여부 확인 필요
# 사용하지 않으면 삭제 권장
```

## DB 스키마 구조

```
auth:
- users ✅
- password_reset_tokens ✅
- user_credits ✅
- credit_transactions ✅
- user_settings ✅

content:
- scenarios ✅
- characters ✅
- worlds ✅
- rank_definitions ✅
- scenario_likes ✅
- scenario_comments ✅
- comment_likes ✅
- scenario_views ✅
- scenario_statistics ✅
- image_mappings ✅

conversation:
- sessions ✅
- dialogues ✅
- user_inputs ✅
- session_snapshots ✅

knowledge:
- entities ✅
- entity_mentions ✅
- entity_relationships ✅
- user_memories ✅

progression:
- user_progression ✅
- user_scenario_progress ✅
- stage_progression ✅
- affinity_records ✅
- xp_transactions ✅
- user_equipment ✅
- game_events ✅
- mission_records ✅

observability:
- logs ✅
- error_logs ✅
- performance_metrics ✅

ml:
- training_logs ✅
- user_feedback ✅

public:
- gallery_images ✅
- gallery_image_likes ✅
- gallery_image_views ✅
- chat_sessions (legacy?)
```

## 우선순위 수정

**HIGH (즉시)**:
1. ✅ public.users 삭제 완료
2. galleries/models.py - 스키마 추가
3. game/models.py - 스키마 추가

**MEDIUM**:
4. logging/models.py - 스키마 추가
5. misc/models.py - 스키마 추가

**LOW**:
6. images/legacy_models.py - 사용 여부 확인
