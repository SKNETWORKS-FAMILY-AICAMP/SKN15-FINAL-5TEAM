"""
백업 파일에서 누락된 테이블의 CREATE TABLE 문을 추출하는 스크립트
Alembic migration 파일 생성용
"""
import re

# 누락된 테이블 목록
missing_tables = [
    # Logging (3개) - 이미 모델 생성됨
    # 'logs', 'error_logs', 'performance_metrics',

    # Credits (3개)
    'user_credits', 'credit_transactions', 'xp_transactions',

    # Game Progression (6개)
    'stage_progression', 'user_progression', 'user_scenario_progress',
    'game_events', 'mission_records', 'rank_definitions',

    # Images (5개)
    'image_assets', 'image_mapping_rules', 'scenario_stage_images',
    'scenario_default_images', 'user_unlocked_images',

    # Scenarios (3개)
    'scenario_statistics', 'scenario_views', 'scenarios',

    # Sessions & Dialogues (3개)
    'dialogues', 'session_snapshots', 'user_inputs',

    # User Settings (2개)
    'user_settings', 'user_equipment',

    # Training/Feedback (2개)
    'training_logs', 'user_feedback',
]

backup_file = "/Users/jtm427/Desktop/workspace/backups/database_backup_20251109_210633.sql"

with open(backup_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 각 테이블의 CREATE TABLE 문 추출
for table in missing_tables:
    # Find CREATE TABLE statement (could be in any schema)
    patterns = [
        (rf'CREATE TABLE statedb\.{table}\s*\((.*?)\);', 'statedb'),
        (rf'CREATE TABLE logdb\.{table}\s*\((.*?)\);', 'logdb'),
        (rf'CREATE TABLE public\.{table}\s*\((.*?)\);', 'public'),
    ]

    for pattern, schema in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            ddl = match.group(1)
            # Remove schema prefix for migration
            full_create = f"CREATE TABLE {table} ({ddl});"

            # Clean up constraint names
            full_create = re.sub(r'statedb\.', '', full_create)
            full_create = re.sub(r'logdb\.', '', full_create)
            full_create = re.sub(r'public\.', '', full_create)

            print(f"-- Table: {table} (from {schema})")
            print(full_create)
            print()
            break
