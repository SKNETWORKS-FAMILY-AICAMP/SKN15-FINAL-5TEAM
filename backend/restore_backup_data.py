"""
백업 데이터 복원 스크립트
- schema prefix 제거 (logdb., statedb., public. -> public.)
- 외래키 의존성 순서에 맞춰 데이터 복원
"""
import re
import subprocess
from pathlib import Path

# 백업 파일 경로
BACKUP_FILE = "/Users/jtm427/Desktop/workspace/backups/database_backup_20251109_210633.sql"

# 데이터베이스 연결 정보
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "kimedb"
DB_USER = "kime"
DB_PASSWORD = "dev123"

# 복원 순서 (외래키 의존성 고려)
# 1순위: 독립 테이블 (외래키 없음)
# 2순위: users 의존 테이블
# 3순위: sessions 의존 테이블
# 4순위: 기타 의존 테이블
RESTORE_ORDER = [
    # 1순위: 독립 테이블
    "rank_definitions",
    "scenarios",
    "image_assets",

    # 2순위: users 테이블 필수 (먼저 복원되어야 함)
    "users",

    # 3순위: users 의존 테이블
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

    # 4순위: scenarios 의존 테이블
    "scenario_statistics",
    "scenario_views",
    "scenario_comments",
    "scenario_likes",
    "scenario_default_images",
    "scenario_stage_images",

    # 5순위: sessions 테이블 (users 이후)
    "sessions",

    # 6순위: sessions 의존 테이블
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

    # 7순위: entities 관련
    "entities",
    "entity_mentions",
    "entity_relationships",

    # 8순위: 기타
    "comment_likes",
    "image_mapping_rules",
    "user_unlocked_images",
    "training_logs",
    "user_feedback",
]

def extract_table_data(backup_content, table_name):
    """
    백업 파일에서 특정 테이블의 COPY 문 추출
    스키마 prefix (logdb., statedb., public.) 제거
    """
    # 다양한 스키마에서 테이블을 찾을 수 있도록 패턴 작성
    patterns = [
        rf'COPY statedb\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',
        rf'COPY logdb\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',
        rf'COPY public\.{table_name}\s*\((.*?)\)\s+FROM stdin;(.*?)\\\.',
    ]

    for pattern in patterns:
        match = re.search(pattern, backup_content, re.DOTALL)
        if match:
            columns = match.group(1)
            data = match.group(2).strip()

            # schema prefix 제거한 COPY 문 생성
            copy_statement = f"COPY {table_name} ({columns}) FROM stdin;\n{data}\n\\.\n"
            return copy_statement

    return None

def restore_table_data(table_name, copy_statement):
    """
    psql을 통해 테이블 데이터 복원
    """
    if not copy_statement:
        print(f"⚠️  Table {table_name}: No data found in backup")
        return False

    try:
        # psql 명령으로 COPY 문 실행
        cmd = [
            "docker", "exec", "-i", "postgresql",
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
            # COPY 결과에서 행 수 추출
            match = re.search(r'COPY (\d+)', stdout)
            row_count = match.group(1) if match else "?"
            print(f"✅ Table {table_name}: {row_count} rows restored")
            return True
        else:
            print(f"❌ Table {table_name}: Error - {stderr}")
            return False

    except Exception as e:
        print(f"❌ Table {table_name}: Exception - {str(e)}")
        return False

def main():
    print("=" * 60)
    print("백업 데이터 복원 시작")
    print("=" * 60)

    # 백업 파일 읽기
    print(f"\n📁 Reading backup file: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
        backup_content = f.read()
    print(f"✅ Backup file loaded ({len(backup_content):,} bytes)")

    # 외래키 제약 조건 임시 비활성화
    print("\n🔓 Disabling foreign key constraints...")
    disable_fk_cmd = [
        "docker", "exec", "postgresql",
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-c", "SET session_replication_role = replica;"
    ]
    subprocess.run(disable_fk_cmd, capture_output=True)

    # 기존 데이터 삭제 (백업 데이터로 교체)
    print("\n🗑️  Truncating existing data...")
    for table_name in reversed(RESTORE_ORDER):
        truncate_cmd = [
            "docker", "exec", "postgresql",
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "-c", f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"
        ]
        result = subprocess.run(truncate_cmd, capture_output=True, text=True)
        if result.returncode != 0 and "does not exist" not in result.stderr:
            print(f"⚠️  Warning truncating {table_name}: {result.stderr}")
    print("✅ All tables truncated")

    # 테이블별 데이터 복원
    print(f"\n📊 Restoring {len(RESTORE_ORDER)} tables in dependency order...")
    print("-" * 60)

    success_count = 0
    skip_count = 0
    error_count = 0

    for table_name in RESTORE_ORDER:
        copy_statement = extract_table_data(backup_content, table_name)

        if copy_statement:
            if restore_table_data(table_name, copy_statement):
                success_count += 1
            else:
                error_count += 1
        else:
            skip_count += 1
            print(f"⏭️  Table {table_name}: Skipped (no data in backup)")

    # 외래키 제약 조건 재활성화
    print("\n🔒 Re-enabling foreign key constraints...")
    enable_fk_cmd = [
        "docker", "exec", "postgresql",
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-c", "SET session_replication_role = DEFAULT;"
    ]
    subprocess.run(enable_fk_cmd, capture_output=True)

    # Sequence 값 재설정 (bigserial/serial 컬럼용)
    print("\n🔢 Updating sequences for auto-increment columns...")
    sequence_tables = [
        "logs", "error_logs", "performance_metrics",
        "dialogues", "dialogue_turns", "session_snapshots", "user_inputs",
        "stage_progression", "game_events", "mission_records",
        "affinity_records", "entity_mentions", "entity_relationships",
        "training_logs", "user_feedback", "entities",
    ]

    for table in sequence_tables:
        seq_cmd = f"""
        SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                      COALESCE((SELECT MAX(id) FROM {table}), 1),
                      true);
        """
        subprocess.run([
            "docker", "exec", "postgresql",
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "-c", seq_cmd
        ], capture_output=True)

    print("✅ Sequences updated")

    # 결과 요약
    print("\n" + "=" * 60)
    print("복원 완료 요약")
    print("=" * 60)
    print(f"✅ Success: {success_count} tables")
    print(f"⏭️  Skipped: {skip_count} tables (no data)")
    print(f"❌ Errors:  {error_count} tables")
    print("=" * 60)

    # 각 테이블의 행 수 확인
    print("\n📊 Final row counts:")
    print("-" * 60)

    for table in RESTORE_ORDER:
        count_cmd = [
            "docker", "exec", "postgresql",
            "psql", "-U", DB_USER, "-d", DB_NAME,
            "-t", "-c", f"SELECT COUNT(*) FROM {table};"
        ]
        result = subprocess.run(count_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            count = result.stdout.strip()
            print(f"{table:30s}: {count:>8s} rows")

if __name__ == "__main__":
    main()
