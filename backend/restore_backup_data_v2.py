"""
백업 데이터 복원 스크립트 v2
- 스키마 불일치 처리 (컬럼 매핑)
- 테이블별 커스텀 변환 로직
"""
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# 백업 파일 경로
BACKUP_FILE = "/Users/jtm427/Desktop/workspace/backups/database_backup_20251109_210633.sql"

# 데이터베이스 연결 정보
DB_CONTAINER = "postgresql"
DB_NAME = "kimedb"
DB_USER = "kime"

# 테이블별 컬럼 매핑 (백업 -> 현재 스키마)
COLUMN_MAPPINGS = {
    "users": {
        # 백업 컬럼: (user_id, username, email, password_hash, provider, display_name, created_at, updated_at, last_login, is_active)
        # 현재 컬럼: (user_id, username, password_hash, display_name, email, is_active, is_verified, role, total_sessions, total_bubbles, last_login_at, created_at, updated_at)
        "columns": "(user_id, username, password_hash, display_name, email, is_active, is_verified, role, total_sessions, total_bubbles, last_login_at, created_at, updated_at)",
        "transform": lambda data: transform_users_data(data)
    },
    "sessions": {
        # 백업 sessions 테이블이 현재 스키마와 다를 수 있음
        "columns": None,  # 백업 스키마 그대로 사용
        "transform": None
    }
}

def transform_users_data(backup_data: str) -> str:
    """
    users 테이블 데이터 변환
    백업 형식: user_id, username, email, password_hash, provider, display_name, created_at, updated_at, last_login, is_active
    현재 형식: user_id, username, password_hash, display_name, email, is_active, is_verified, role, total_sessions, total_bubbles, last_login_at, created_at, updated_at
    """
    lines = []
    for line in backup_data.strip().split('\n'):
        if not line or line == '\\.':
            continue

        fields = line.split('\t')
        if len(fields) < 10:
            continue

        user_id = fields[0]
        username = fields[1]
        email = fields[2] if fields[2] != '\\N' else '\\N'
        password_hash = fields[3]
        # provider = fields[4]  # 무시
        display_name = fields[5]
        created_at = fields[6]
        updated_at = fields[7]
        last_login = fields[8]  # last_login -> last_login_at
        is_active = fields[9]

        # 새 컬럼 추가 (NOT NULL 제약조건 만족)
        is_verified = 't'  # 기본값: true
        role = 'user'  # 기본값: user
        total_sessions = '0'  # 기본값: 0
        total_bubbles = '0'  # 기본값: 0

        # 새 형식으로 재구성
        # 순서: user_id, username, password_hash, display_name, email, is_active, is_verified, role, total_sessions, total_bubbles, last_login_at, created_at, updated_at
        new_line = f"{user_id}\t{username}\t{password_hash}\t{display_name}\t{email}\t{is_active}\t{is_verified}\t{role}\t{total_sessions}\t{total_bubbles}\t{last_login}\t{created_at}\t{updated_at}"
        lines.append(new_line)

    return '\n'.join(lines)

def extract_table_data_from_backup(backup_content: str, table_name: str) -> Optional[Tuple[str, str]]:
    """
    백업 파일에서 특정 테이블의 COPY 문 추출
    Returns: (columns, data) tuple or None
    """
    patterns = [
        (rf'COPY statedb\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',  'statedb'),
        (rf'COPY logdb\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',    'logdb'),
        (rf'COPY public\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',   'public'),
    ]

    for pattern, schema in patterns:
        match = re.search(pattern, backup_content, re.DOTALL)
        if match:
            columns = match.group(1).strip()
            data = match.group(2).strip()
            return (columns, data)

    return None

def restore_table(table_name: str, backup_content: str) -> bool:
    """
    테이블 데이터 복원
    """
    result = extract_table_data_from_backup(backup_content, table_name)
    if not result:
        print(f"⏭️  {table_name:30s}: No data in backup")
        return False

    backup_columns, backup_data = result

    # 테이블별 커스텀 매핑 적용
    if table_name in COLUMN_MAPPINGS:
        mapping = COLUMN_MAPPINGS[table_name]

        # 컬럼 매핑
        if mapping["columns"]:
            target_columns = mapping["columns"]
        else:
            target_columns = f"({backup_columns})"

        # 데이터 변환
        if mapping["transform"]:
            transformed_data = mapping["transform"](backup_data)
        else:
            transformed_data = backup_data
    else:
        # 매핑 없으면 백업 그대로 사용
        target_columns = f"({backup_columns})"
        transformed_data = backup_data

    # COPY 문 생성
    copy_statement = f"COPY {table_name} {target_columns} FROM stdin;\n{transformed_data}\n\\.\n"

    # psql로 실행
    try:
        cmd = [
            "docker", "exec", "-i", DB_CONTAINER,
            "psql", "-U", DB_USER, "-d", DB_NAME
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=copy_statement)

        if process.returncode == 0:
            match = re.search(r'COPY (\d+)', stdout)
            row_count = match.group(1) if match else "?"
            print(f"✅ {table_name:30s}: {row_count:>6s} rows")
            return True
        else:
            # 에러 메시지 출력
            error_msg = stderr.strip().split('\n')[0] if stderr else "Unknown error"
            print(f"❌ {table_name:30s}: {error_msg}")
            return False

    except Exception as e:
        print(f"❌ {table_name:30s}: Exception - {str(e)}")
        return False

# 복원 순서 (외래키 의존성 고려)
RESTORE_ORDER = [
    # 독립 테이블
    "rank_definitions",
    "scenarios",
    "entities",
    "image_assets",

    # users 필수
    "users",

    # users 의존
    "user_credits",
    "user_equipment",
    "user_settings",
    "user_progression",
    "user_scenario_progress",
    "user_character_affinity",
    "credit_transactions",
    "xp_transactions",
    "password_reset_tokens",
    "user_memories",

    # scenarios 의존
    "scenario_statistics",
    "scenario_views",
    "scenario_comments",
    "scenario_likes",
    "scenario_default_images",
    "scenario_stage_images",

    # sessions
    "sessions",

    # sessions 의존
    "dialogues",
    "dialogue_turns",
    "session_snapshots",
    "user_inputs",
    "stage_progression",
    "game_events",
    "mission_records",
    "affinity_records",
    "gallery_images",
    "logs",
    "error_logs",
    "performance_metrics",
    "entity_mentions",
    "entity_relationships",

    # 기타
    "comment_likes",
    "image_mapping_rules",
    "user_unlocked_images",
    "training_logs",
    "user_feedback",
]

def main():
    print("=" * 70)
    print("백업 데이터 복원 시작 (v2 - Column Mapping)")
    print("=" * 70)

    # 백업 파일 읽기
    print(f"\n📁 Reading: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        backup_content = f.read()
    print(f"✅ Loaded ({len(backup_content):,} bytes)")

    # FK 제약 비활성화
    print("\n🔓 Disabling constraints...")
    subprocess.run([
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-c", "SET session_replication_role = replica;"
    ], capture_output=True)

    # 테이블 초기화
    print("🗑️  Truncating tables...")
    for table_name in reversed(RESTORE_ORDER):
        subprocess.run([
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "-c", f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"
        ], capture_output=True, text=True)
    print("✅ Truncated")

    # 데이터 복원
    print(f"\n📊 Restoring {len(RESTORE_ORDER)} tables...")
    print("-" * 70)

    success = 0
    skipped = 0
    errors = 0

    for table_name in RESTORE_ORDER:
        if restore_table(table_name, backup_content):
            success += 1
        elif table_name in COLUMN_MAPPINGS or extract_table_data_from_backup(backup_content, table_name):
            errors += 1
        else:
            skipped += 1

    # FK 제약 재활성화
    print("\n🔒 Re-enabling constraints...")
    subprocess.run([
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-c", "SET session_replication_role = DEFAULT;"
    ], capture_output=True)

    # Sequence 업데이트
    print("🔢 Updating sequences...")
    for table in ["logs", "error_logs", "performance_metrics", "dialogues", "entities", "training_logs"]:
        subprocess.run([
            "docker", "exec", DB_CONTAINER,
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "-c", f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1), true);"
        ], capture_output=True)
    print("✅ Sequences updated")

    # 결과
    print("\n" + "=" * 70)
    print("복원 완료")
    print("=" * 70)
    print(f"✅ Success: {success}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Errors:  {errors}")
    print("=" * 70)

if __name__ == "__main__":
    main()
