"""
백업 파일에서 누락된 테이블의 DDL을 추출하는 스크립트
"""
import re

# 현재 있는 테이블 목록
existing_tables = {
    'affinity_records', 'comment_likes', 'dialogue_turns', 'entities',
    'entity_mentions', 'entity_relationships', 'gallery_images',
    'password_reset_tokens', 'scenario_comments', 'scenario_likes',
    'sessions', 'user_character_affinity', 'user_memories', 'users'
}

# merge_strategy.md에서 명시된 필수 테이블 (42개)
required_tables = {
    # statedb (37개)
    'sessions', 'user_inputs', 'dialogues', 'affinity_records',
    'stage_progression', 'game_events', 'mission_records',
    'session_snapshots', 'users', 'password_reset_tokens',
    'user_credits', 'credit_transactions', 'user_settings',
    'user_memories', 'rank_definitions', 'user_progression',
    'user_equipment', 'xp_transactions', 'scenarios',
    'scenario_statistics', 'user_scenario_progress',
    'scenario_views', 'scenario_comments', 'comment_likes',
    'scenario_likes', 'image_assets', 'scenario_stage_images',
    'image_mapping_rules', 'scenario_default_images',
    'user_unlocked_images', 'user_character_affinity',
    'entities', 'entity_relationships', 'entity_mentions',
    # logdb (3개)
    'logs', 'error_logs', 'performance_metrics',
    # public (2개)
    'training_logs', 'user_feedback',
}

# 누락된 테이블
missing_tables = required_tables - existing_tables

print("=" * 80)
print(f"총 필요 테이블: {len(required_tables)}개")
print(f"현재 존재 테이블: {len(existing_tables)}개")
print(f"누락된 테이블: {len(missing_tables)}개")
print("=" * 80)

print("\n누락된 테이블 목록:")
for table in sorted(missing_tables):
    print(f"  - {table}")

# 백업 파일에서 누락된 테이블의 CREATE TABLE 문 추출
backup_file = "/Users/jtm427/Desktop/workspace/backups/database_backup_20251109_210633.sql"

with open(backup_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 각 테이블의 CREATE TABLE 문을 추출
print("\n\n" + "=" * 80)
print("누락된 테이블의 DDL 추출")
print("=" * 80)

for table in sorted(missing_tables):
    # Find CREATE TABLE statement for this table
    # Could be in statedb, logdb, or public schema
    patterns = [
        rf'CREATE TABLE statedb\.{table}\s*\((.*?)\);',
        rf'CREATE TABLE logdb\.{table}\s*\((.*?)\);',
        rf'CREATE TABLE public\.{table}\s*\((.*?)\);',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            ddl = match.group(1)
            # Clean up and format
            lines = [line.strip() for line in ddl.split('\n') if line.strip()]

            print(f"\n{'=' * 80}")
            print(f"TABLE: {table}")
            print(f"{'=' * 80}")
            for line in lines[:30]:  # First 30 lines
                print(line)
            break
