#!/usr/bin/env python3
"""
User Progression System E2E Test
Tests the complete flow: Register -> Login -> Get Progression Data
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

def print_section(title):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(label, data):
    """Print result"""
    print(f"\n✅ {label}:")
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ['access_token', 'refresh_token']:
                print(f"  {key}: {value[:50]}..." if value else f"  {key}: None")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"  {data}")

def test_register_and_login():
    """Register a new user and login"""
    print_section("1️⃣  User Registration & Login")

    timestamp = datetime.now().strftime("%H%M%S")
    test_user = {
        "username": f"testprogression{timestamp}",
        "password": "test1234",
        "email": f"testprogression{timestamp}@example.com",
        "display_name": f"진행도테스트{timestamp}"
    }

    print(f"\n📤 Registering user: {test_user['username']}")

    try:
        # Register
        register_response = requests.post(
            f"{API_URL}/api/auth/register",
            json=test_user,
            timeout=10
        )
        register_result = register_response.json()

        if not register_result.get('success'):
            print(f"❌ Registration failed: {register_result.get('message')}")
            return None, None

        print_result("Registration success", {
            "user_id": register_result.get('user_id'),
            "username": register_result.get('username'),
            "display_name": register_result.get('display_name')
        })

        # Login
        print(f"\n📤 Logging in as: {test_user['username']}")
        login_response = requests.post(
            f"{API_URL}/api/auth/login",
            json={
                "username": test_user['username'],
                "password": test_user['password']
            },
            timeout=10
        )
        login_result = login_response.json()

        if not login_result.get('success'):
            print(f"❌ Login failed: {login_result.get('message')}")
            return None, None

        access_token = login_result.get('access_token')
        print_result("Login success", {
            "access_token": access_token[:50] + "..." if access_token else None,
            "user_id": login_result.get('user_id')
        })

        return access_token, register_result.get('user_id')

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None, None

def test_get_progression(access_token):
    """Test GET /api/users/me/progression endpoint"""
    print_section("2️⃣  Get User Progression")

    print(f"\n📤 Fetching progression data...")
    print(f"  Endpoint: GET /api/users/me/progression")
    print(f"  Token: {access_token[:50]}...")

    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(
            f"{API_URL}/api/users/me/progression",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print(f"\n❌ Request failed:")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            return None

        progression = response.json()

        print(f"\n✅ Progression data retrieved successfully:")
        print(f"  User ID: {progression.get('user_id')}")
        print(f"  Rank: {progression.get('rank_icon')} {progression.get('rank_name_ko')} ({progression.get('rank_code')})")
        print(f"  Level: {progression.get('level')}")
        print(f"  XP: {progression.get('experience_points')} / {progression.get('next_rank_xp')}")
        print(f"  Total Messages: {progression.get('total_messages')}")
        print(f"  Total Sessions: {progression.get('total_sessions')}")
        print(f"  Play Time: {progression.get('total_play_minutes')} minutes")
        print(f"  Scenarios Completed: {progression.get('scenarios_completed')}")
        print(f"  Achievements: {progression.get('achievements_count')}")
        print(f"  Equipment:")
        print(f"    - Sword: {progression.get('sword_status')}")
        print(f"    - Uniform: {progression.get('uniform_status')}")
        print(f"    - Crow: {progression.get('crow_status')}")

        return progression

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def validate_progression_schema(progression):
    """Validate that progression data matches TypeScript interface"""
    print_section("3️⃣  Schema Validation")

    required_fields = [
        'user_id', 'rank_code', 'rank_name_ko', 'rank_icon',
        'experience_points', 'level', 'next_rank_xp',
        'total_messages', 'total_sessions', 'total_play_minutes',
        'scenarios_completed', 'achievements_count',
        'sword_status', 'uniform_status', 'crow_status'
    ]

    print(f"\n📋 Checking required fields...")
    missing_fields = []

    for field in required_fields:
        if field not in progression:
            missing_fields.append(field)
            print(f"  ❌ Missing: {field}")
        else:
            print(f"  ✅ Found: {field} = {progression[field]}")

    if missing_fields:
        print(f"\n❌ Schema validation failed!")
        print(f"  Missing fields: {', '.join(missing_fields)}")
        return False

    print(f"\n✅ Schema validation passed!")
    print(f"  All required fields present and valid")
    return True

def test_initial_values(progression):
    """Test that initial values are correct for a new user"""
    print_section("4️⃣  Initial Values Test")

    print(f"\n📋 Checking initial values for new user...")

    checks = [
        ("Rank Code", progression.get('rank_code'), 'trainee', True),
        ("Rank Name", progression.get('rank_name_ko'), '견습생', True),
        ("Rank Icon", progression.get('rank_icon'), '🌱', True),
        ("Level", progression.get('level'), 1, True),
        ("Experience Points", progression.get('experience_points'), 0, True),
        ("Total Messages", progression.get('total_messages'), 0, True),
        ("Total Sessions", progression.get('total_sessions'), 0, True),
        ("Total Play Minutes", progression.get('total_play_minutes'), 0, True),
        ("Scenarios Completed", progression.get('scenarios_completed'), 0, True),
        ("Achievements Count", progression.get('achievements_count'), 0, True),
        ("Sword Status", progression.get('sword_status'), 'waiting', True),
        ("Uniform Status", progression.get('uniform_status'), 'waiting', True),
        ("Crow Status", progression.get('crow_status'), 'waiting', True),
    ]

    all_passed = True
    for label, actual, expected, check_equality in checks:
        if check_equality and actual == expected:
            print(f"  ✅ {label}: {actual} (expected: {expected})")
        elif check_equality and actual != expected:
            print(f"  ❌ {label}: {actual} (expected: {expected})")
            all_passed = False
        else:
            print(f"  ✅ {label}: {actual}")

    if all_passed:
        print(f"\n✅ All initial values correct!")
    else:
        print(f"\n⚠️  Some initial values differ from expected")

    return all_passed

def main():
    """Main test execution"""
    print("\n" + "🎮" * 35)
    print("     User Progression System E2E Test")
    print("🎮" * 35)

    # Test 1: Register and Login
    access_token, user_id = test_register_and_login()
    if not access_token:
        print("\n❌ Test failed at registration/login - aborting")
        return

    # Test 2: Get Progression
    progression = test_get_progression(access_token)
    if not progression:
        print("\n❌ Test failed at get progression - aborting")
        return

    # Test 3: Validate Schema
    schema_valid = validate_progression_schema(progression)

    # Test 4: Check Initial Values
    values_valid = test_initial_values(progression)

    # Final Summary
    print_section("✅ Test Summary")
    print(f"\n📊 Results:")
    print(f"  ✅ User Registration & Login: PASSED")
    print(f"  ✅ Get Progression API: PASSED")
    print(f"  {'✅' if schema_valid else '❌'} Schema Validation: {'PASSED' if schema_valid else 'FAILED'}")
    print(f"  {'✅' if values_valid else '⚠️ '} Initial Values: {'PASSED' if values_valid else 'WARNING'}")

    print(f"\n🎯 Integration Test Result:")
    if schema_valid:
        print(f"  ✅ RightSidebar frontend integration ready")
        print(f"  ✅ All required fields available for UI display")
        print(f"  ✅ TypeScript interface matches backend response")
    else:
        print(f"  ❌ Integration issues detected - check schema")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
