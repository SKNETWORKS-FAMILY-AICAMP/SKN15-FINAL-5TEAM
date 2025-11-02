#!/usr/bin/env python3
"""
Scenario Database Seeding Script
Seeds the database with existing 6 scenarios from HomePage

Usage:
  python seed_scenarios.py                # Use .env.local (local DB)
  python seed_scenarios.py production     # Use .env.production (RDS)
"""
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path to import DatabaseManager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.db_manager import DatabaseManager

# Get database config from environment variables or use defaults
def get_db_config(env='local'):
    """Get DB config from environment variables or use defaults"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'dbname': os.getenv('DB_NAME', 'kimedb'),
        'user': os.getenv('DB_USER', 'kime'),
        'password': os.getenv('DB_PASSWORD', 'dev123')
    }

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

# Scenario data from HomePage.tsx (lines 30-103)
SCENARIOS = [
    {
        'scenario_id': 'tanjiro',
        'title': '편의점 알바생 탄지로',
        'description': '탄지로와 함께하는 편의점 일상 체험',
        'image_url': '/images/편의점탄지로.png',
        'thumbnail_url': '/images/편의점탄지로.png',
        'tags': ['편의점', '일상', '탄지로'],
        'card_size': 'normal',
        'route_path': '/chat/tanjiro',
        'display_order': 1,
        # Initial statistics from HomePage hardcoded values
        'initial_likes': 121,
        'initial_comments': 45,
        'initial_views': 1200
    },
    {
        'scenario_id': 'train',
        'title': '무한열차',
        'description': '열차 안에서 벌어지는 사건에 휘말려 캐릭터들과 협력하여 생존 및 해결을 도모',
        'image_url': '/images/무한열차.jpeg',
        'thumbnail_url': '/images/무한열차.jpeg',
        'tags': ['무한열차', '꿈속전투', '엔무'],
        'card_size': 'normal',
        'route_path': '/character/train',
        'display_order': 2,
        'initial_likes': 98,
        'initial_comments': 32,
        'initial_views': 890
    },
    {
        'scenario_id': 'infinity-castle',
        'title': '무한성',
        'description': '최종 결전을 배경으로, 캐릭터들과 함께 전략을 세우며 전투 직전의 긴장감을 체험',
        'image_url': '/images/무한성.webp',
        'thumbnail_url': '/images/무한성.webp',
        'tags': ['최종결전', '귀살대', '무잔전'],
        'card_size': 'large',  # Featured scenario
        'route_path': '/character/infinity-castle',
        'display_order': 3,
        'initial_likes': 156,
        'initial_comments': 67,
        'initial_views': 1850
    },
    {
        'scenario_id': 'ending',
        'title': '엔딩 이후',
        'description': '최종 결전 후 동료들과 함께하는 평범하지만 소중한 일상. 탄지로, 젠이츠, 이노스케와 함께 마을 순찰과 훈련을 하며 서로를 돌보는 따뜻한 이야기',
        'image_url': '/images/엔딩이후.png',
        'thumbnail_url': '/images/엔딩이후.png',
        'tags': ['엔딩이후', '일상', '평화', '동료애'],
        'card_size': 'normal',
        'route_path': '/chat/ending',
        'display_order': 4,
        'initial_likes': 87,
        'initial_comments': 28,
        'initial_views': 720
    },
    {
        'scenario_id': 'counseling',
        'title': '귀칼 상담소 AU',
        'description': '캐릭터들이 상담사가 되어 서로의 고민을 풀어가는 힐링 스토리',
        'image_url': '/images/귀칼상담소.png',
        'thumbnail_url': '/images/귀칼상담소.png',
        'tags': ['상담소', '힐링AU', '감정공감'],
        'card_size': 'normal',
        'route_path': '/chat/counseling',
        'display_order': 5,
        'initial_likes': 134,
        'initial_comments': 52,
        'initial_views': 1150
    },
    {
        'scenario_id': 'idol',
        'title': '아이돌/밴드 AU',
        'description': '귀멸 캐릭터들이 아이돌 그룹으로 활동, 매니저 or 팬클럽으로서 그들의 성장과 무대를 지켜봄',
        'image_url': '/images/아이돌밴드.png',
        'thumbnail_url': '/images/아이돌밴드.png',
        'tags': ['아이돌AU', '밴드AU', '팬심폭발'],
        'card_size': 'normal',
        'route_path': '/chat/idol',
        'display_order': 6,
        'initial_likes': 203,
        'initial_comments': 89,
        'initial_views': 2100
    }
]

def seed_scenarios(db: DatabaseManager):
    """Insert scenarios into database"""
    print_header("Seeding Scenarios")

    success_count = 0
    error_count = 0

    for scenario in SCENARIOS:
        try:
            scenario_id = scenario['scenario_id']

            # Check if already exists
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT scenario_id FROM statedb.scenarios WHERE scenario_id = %s",
                        (scenario_id,)
                    )
                    exists = cur.fetchone()

                    if exists:
                        print(f"⚠️  Scenario '{scenario_id}' already exists, skipping...")
                        continue

                    # Insert scenario
                    cur.execute("""
                        INSERT INTO statedb.scenarios (
                            scenario_id, title, description, image_url, thumbnail_url,
                            tags, card_size, route_path, display_order, is_active
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        scenario_id,
                        scenario['title'],
                        scenario['description'],
                        scenario['image_url'],
                        scenario['thumbnail_url'],
                        scenario['tags'],
                        scenario['card_size'],
                        scenario['route_path'],
                        scenario['display_order'],
                        True  # is_active
                    ))

            print_success(f"Inserted scenario: {scenario_id} - {scenario['title']}")
            success_count += 1

        except Exception as e:
            print_error(f"Failed to insert scenario '{scenario_id}': {e}")
            error_count += 1

    print(f"\n📊 Scenarios: {success_count} inserted, {error_count} errors")
    return success_count, error_count

def seed_statistics(db: DatabaseManager):
    """Insert initial statistics for scenarios"""
    print_header("Seeding Scenario Statistics")

    success_count = 0
    error_count = 0

    for scenario in SCENARIOS:
        try:
            scenario_id = scenario['scenario_id']

            # Check if already exists
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT scenario_id FROM statedb.scenario_statistics WHERE scenario_id = %s",
                        (scenario_id,)
                    )
                    exists = cur.fetchone()

                    if exists:
                        print(f"⚠️  Statistics for '{scenario_id}' already exist, skipping...")
                        continue

                    # Insert statistics
                    cur.execute("""
                        INSERT INTO statedb.scenario_statistics (
                            scenario_id, total_likes, total_comments, total_views,
                            total_completions, total_sessions, avg_session_duration
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        scenario_id,
                        scenario['initial_likes'],
                        scenario['initial_comments'],
                        scenario['initial_views'],
                        0,  # total_completions (starts at 0)
                        0,  # total_sessions (starts at 0)
                        0   # avg_session_duration (starts at 0)
                    ))

            print_success(f"Inserted statistics: {scenario_id} (likes: {scenario['initial_likes']}, views: {scenario['initial_views']})")
            success_count += 1

        except Exception as e:
            print_error(f"Failed to insert statistics for '{scenario_id}': {e}")
            error_count += 1

    print(f"\n📊 Statistics: {success_count} inserted, {error_count} errors")
    return success_count, error_count

def verify_seed(db: DatabaseManager):
    """Verify seeding was successful"""
    print_header("Verification")

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Count scenarios
                cur.execute("SELECT COUNT(*) FROM statedb.scenarios")
                scenario_count = cur.fetchone()[0]

                # Count statistics
                cur.execute("SELECT COUNT(*) FROM statedb.scenario_statistics")
                stats_count = cur.fetchone()[0]

                # Query view
                cur.execute("SELECT COUNT(*) FROM statedb.v_scenario_cards")
                view_count = cur.fetchone()[0]

        print_success(f"Scenarios table: {scenario_count} records")
        print_success(f"Statistics table: {stats_count} records")
        print_success(f"View (v_scenario_cards): {view_count} records")

        if scenario_count == len(SCENARIOS) and stats_count == len(SCENARIOS):
            print_success("\n✨ All scenarios seeded successfully!")
            return True
        else:
            print_error(f"\n⚠️  Expected {len(SCENARIOS)} records, but found {scenario_count} scenarios and {stats_count} statistics")
            return False

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("\n" + "🌱" * 35)
    print("     Scenario Database Seeding Script")
    print("🌱" * 35)

    # Check environment argument
    env = sys.argv[1] if len(sys.argv) > 1 else 'local'

    # Load appropriate .env file
    if env == 'production':
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env.production')
        print(f"\n🌍 Environment: PRODUCTION")
        print(f"📄 Loading: {env_file}")
    else:
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env.local')
        print(f"\n🌍 Environment: LOCAL")
        print(f"📄 Loading: {env_file}")

    load_dotenv(dotenv_path=env_file, override=True)

    # Get DB config and create DB manager
    try:
        db_config = get_db_config(env)

        print(f"\n📡 Connecting to database: {db_config['host']}:{db_config['port']}/{db_config['dbname']}")
        db = DatabaseManager(
            host=db_config['host'],
            port=db_config['port'],
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password']
        )
        print_success("Database connection established")

    except Exception as e:
        print_error(f"Failed to connect to database: {e}")
        sys.exit(1)

    # Seed scenarios
    scenario_success, scenario_errors = seed_scenarios(db)

    # Seed statistics
    stats_success, stats_errors = seed_statistics(db)

    # Verify
    verification_passed = verify_seed(db)

    # Summary
    print_header("Summary")
    print(f"\n📊 Seeding Results:")
    print(f"  ✅ Scenarios: {scenario_success} inserted")
    print(f"  ✅ Statistics: {stats_success} inserted")
    print(f"  ❌ Errors: {scenario_errors + stats_errors}")
    print(f"  {'✅' if verification_passed else '❌'} Verification: {'PASSED' if verification_passed else 'FAILED'}")

    if verification_passed:
        print("\n🎉 Seeding complete! HomePage can now load scenarios from database.")
        print("\nNext steps:")
        print("  1. Add DB Manager methods for scenario CRUD (Phase 2.3)")
        print("  2. Create API endpoints (Phase 2.4)")
        print("  3. Update HomePage to use API (Phase 2.5)")
    else:
        print("\n⚠️  Seeding completed with issues. Please review errors above.")
        sys.exit(1)

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
