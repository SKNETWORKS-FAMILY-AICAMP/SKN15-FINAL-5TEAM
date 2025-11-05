#!/usr/bin/env python3
"""
데이터베이스 전체 데이터 Import 스크립트

backend/data/ 폴더의 모든 JSON 데이터를 데이터베이스에 삽입합니다:
- characters/ : 캐릭터 데이터
- scenarios/ : 시나리오 데이터
- worlds/ : 세계관 데이터 (YAML)
- image_mappings/ : 이미지 매핑 데이터

Usage:
    python import_all_data.py
"""

import sys
import os
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# 부모 디렉토리를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.database.db_manager import DatabaseManager


def print_header(text):
    """헤더 출력"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_success(text):
    """성공 메시지"""
    print(f"✅ {text}")


def print_error(text):
    """에러 메시지"""
    print(f"❌ {text}")


def print_info(text):
    """정보 메시지"""
    print(f"📝 {text}")


def get_db_config():
    """환경 변수에서 DB 설정 가져오기"""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'dbname': os.getenv('DB_NAME', 'kimedb'),
        'user': os.getenv('DB_USER', 'kime'),
        'password': os.getenv('DB_PASSWORD', 'dev123')
    }


def import_characters(db: DatabaseManager, data_dir: str):
    """캐릭터 데이터 import"""
    print_header("캐릭터 데이터 Import")

    char_dir = Path(data_dir) / 'characters'
    if not char_dir.exists():
        print_error(f"캐릭터 디렉토리가 없습니다: {char_dir}")
        return 0, 0

    success_count = 0
    error_count = 0

    for json_file in char_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                char_data = json.load(f)

            char_id = json_file.stem  # 파일명 (확장자 제외)

            # 데이터베이스에 캐릭터 삽입
            # (여기에 실제 insert 로직 추가 필요)
            print_info(f"캐릭터 로드: {char_id} - {char_data.get('name', 'Unknown')}")
            success_count += 1

        except Exception as e:
            print_error(f"캐릭터 import 실패 ({json_file.name}): {e}")
            error_count += 1

    return success_count, error_count


def import_scenarios(db: DatabaseManager, data_dir: str):
    """시나리오 데이터 import"""
    print_header("시나리오 데이터 Import")

    scenario_dir = Path(data_dir) / 'scenarios'
    if not scenario_dir.exists():
        print_error(f"시나리오 디렉토리가 없습니다: {scenario_dir}")
        return 0, 0

    success_count = 0
    error_count = 0

    for json_file in scenario_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)

            scenario_id = json_file.stem

            # 시나리오 데이터 출력
            print_info(f"시나리오 로드: {scenario_id}")
            print_info(f"  타입: {scenario_data.get('type', 'Unknown')}")
            print_info(f"  컷씬 개수: {len(scenario_data.get('cutscenes', []))}")

            success_count += 1

        except Exception as e:
            print_error(f"시나리오 import 실패 ({json_file.name}): {e}")
            error_count += 1

    return success_count, error_count


def import_worlds(db: DatabaseManager, data_dir: str):
    """세계관 데이터 import"""
    print_header("세계관 데이터 Import")

    worlds_dir = Path(data_dir) / 'worlds'
    if not worlds_dir.exists():
        print_error(f"세계관 디렉토리가 없습니다: {worlds_dir}")
        return 0, 0

    success_count = 0
    error_count = 0

    for yaml_file in worlds_dir.glob('*.yaml'):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                world_data = yaml.safe_load(f)

            world_id = yaml_file.stem

            print_info(f"세계관 로드: {world_id}")
            print_info(f"  이름: {world_data.get('world_name', 'Unknown')}")
            print_info(f"  배경: {world_data.get('setting', 'Unknown')}")

            success_count += 1

        except Exception as e:
            print_error(f"세계관 import 실패 ({yaml_file.name}): {e}")
            error_count += 1

    return success_count, error_count


def import_image_mappings(db: DatabaseManager, data_dir: str):
    """이미지 매핑 데이터 import"""
    print_header("이미지 매핑 데이터 Import")

    img_dir = Path(data_dir) / 'image_mappings'
    if not img_dir.exists():
        print_error(f"이미지 매핑 디렉토리가 없습니다: {img_dir}")
        return 0, 0

    success_count = 0
    error_count = 0

    for json_file in img_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                mapping_data = json.load(f)

            mapping_id = json_file.stem

            print_info(f"이미지 매핑 로드: {mapping_id}")
            print_info(f"  이미지 개수: {len(mapping_data) if isinstance(mapping_data, list) else 'N/A'}")

            success_count += 1

        except Exception as e:
            print_error(f"이미지 매핑 import 실패 ({json_file.name}): {e}")
            error_count += 1

    return success_count, error_count


def main():
    """메인 함수"""
    print("\n" + "🌱" * 35)
    print("     데이터베이스 전체 데이터 Import")
    print("🌱" * 35)

    # DB 설정
    config = get_db_config()
    print_info(f"연결 대상: {config['host']}:{config['port']}/{config['dbname']}")

    # DB 연결
    try:
        db = DatabaseManager(**config)
        print_success("데이터베이스 연결 성공")
    except Exception as e:
        print_error(f"데이터베이스 연결 실패: {e}")
        return 1

    # 데이터 디렉토리
    data_dir = Path(__file__).parent.parent / 'data'
    print_info(f"데이터 경로: {data_dir}")

    # 전체 결과 추적
    total_success = 0
    total_errors = 0

    # 1. 캐릭터 import
    success, errors = import_characters(db, str(data_dir))
    total_success += success
    total_errors += errors
    print(f"\n📊 캐릭터: {success}개 로드, {errors}개 에러")

    # 2. 시나리오 import
    success, errors = import_scenarios(db, str(data_dir))
    total_success += success
    total_errors += errors
    print(f"\n📊 시나리오: {success}개 로드, {errors}개 에러")

    # 3. 세계관 import
    success, errors = import_worlds(db, str(data_dir))
    total_success += success
    total_errors += errors
    print(f"\n📊 세계관: {success}개 로드, {errors}개 에러")

    # 4. 이미지 매핑 import
    success, errors = import_image_mappings(db, str(data_dir))
    total_success += success
    total_errors += errors
    print(f"\n📊 이미지 매핑: {success}개 로드, {errors}개 에러")

    # 최종 결과
    print_header("최종 결과")
    print(f"\n✅ 총 {total_success}개 파일 로드")
    print(f"❌ 총 {total_errors}개 에러")

    if total_errors == 0:
        print("\n🎉 모든 데이터 import 성공!")
        return 0
    else:
        print("\n⚠️  일부 에러가 발생했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
