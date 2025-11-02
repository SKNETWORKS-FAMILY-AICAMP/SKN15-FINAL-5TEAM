#!/usr/bin/env python3
"""
End-to-End Testing Script for User Memory System
Tests all memory-related API endpoints, embedding generation, and vector search

Test Coverage:
- Memory CRUD operations (Create, Read, Update, Delete)
- Embedding generation for memories
- Semantic similarity search
- Memory filtering by type
- Session-based memory retrieval
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional

# ============================================================
# Configuration
# ============================================================

API_URL = "http://localhost:8000"

# ANSI color codes for pretty output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.ENDC}\n")

def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

# ============================================================
# Test Helper Functions
# ============================================================

def register_and_login() -> Optional[str]:
    """Register a new test user and login to get access token"""
    timestamp = datetime.now().strftime("%H%M%S%f")
    test_user = {
        "username": f"test_memory_{timestamp}",
        "password": "test1234",
        "email": f"test_memory_{timestamp}@example.com",
        "display_name": f"Test Memory User {timestamp}"
    }

    print_info(f"Registering test user: {test_user['username']}")

    try:
        # Register
        register_response = requests.post(f"{API_URL}/api/auth/register", json=test_user, timeout=10)

        if register_response.status_code != 200:
            print_error(f"Registration failed: {register_response.status_code}")
            print_error(f"Response: {register_response.text}")
            return None

        print_success(f"User registered: {test_user['username']}")

        # Login
        login_response = requests.post(
            f"{API_URL}/api/auth/login",
            json={"username": test_user["username"], "password": test_user["password"]},
            timeout=10
        )

        if login_response.status_code != 200:
            print_error(f"Login failed: {login_response.status_code}")
            print_error(f"Response: {login_response.text}")
            return None

        login_result = login_response.json()
        access_token = login_result.get('access_token')

        if not access_token:
            print_error("No access token in login response")
            return None

        print_success(f"Login successful, token acquired")
        return access_token

    except Exception as e:
        print_error(f"Exception during registration/login: {e}")
        return None

# ============================================================
# Test Functions
# ============================================================

def test_create_memory(access_token: str) -> bool:
    """Test POST /api/users/me/memories (create memory)"""
    print_header("Test 1: Create User Memory")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        memory_data = {
            "memory_key": "favorite_character",
            "memory_value": "렌고쿠를 가장 좋아한다. 그의 열정적인 모습과 불꽃 같은 성격이 멋지다.",
            "memory_type": "character_preference",
            "importance": 0.9,
            "tags": ["character", "preference", "rengoku"],
            "context": {
                "source": "conversation",
                "scenario": "train"
            },
            "confidence": 0.95
        }

        print_info(f"Creating memory: {memory_data['memory_key']}")
        response = requests.post(
            f"{API_URL}/api/users/me/memories",
            headers=headers,
            json=memory_data,
            timeout=30  # Longer timeout for embedding generation
        )

        if response.status_code != 200:
            print_error(f"Request failed: Status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        result = response.json()

        if not result.get('success'):
            print_error("Memory creation failed")
            return False

        print_success(f"Memory created: ID {result.get('memory_id')}")
        print_info(f"Key: {memory_data['memory_key']}")
        print_info(f"Type: {memory_data['memory_type']}")
        print_info(f"Importance: {memory_data['importance']}")

        return True

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_create_multiple_memories(access_token: str) -> bool:
    """Test creating multiple memories with different types"""
    print_header("Test 2: Create Multiple Memories")

    memories = [
        {
            "memory_key": "user_name",
            "memory_value": "사용자의 이름은 태민이다",
            "memory_type": "user_fact",
            "importance": 0.8,
            "tags": ["user", "name"],
        },
        {
            "memory_key": "game_progress_train",
            "memory_value": "무한열차 시나리오를 완료했다. 엔무를 물리치고 승객들을 구했다.",
            "memory_type": "game_progress",
            "importance": 0.7,
            "tags": ["progress", "train", "completed"],
        },
        {
            "memory_key": "relationship_tanjiro",
            "memory_value": "탄지로와 친구가 되었다. 그는 매우 친절하고 따뜻하다.",
            "memory_type": "relationship",
            "importance": 0.75,
            "tags": ["relationship", "tanjiro", "friend"],
        }
    ]

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        success_count = 0

        for memory in memories:
            print_info(f"Creating: {memory['memory_key']}")
            response = requests.post(
                f"{API_URL}/api/users/me/memories",
                headers=headers,
                json=memory,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print_success(f"✓ {memory['memory_key']} (ID: {result.get('memory_id')})")
                    success_count += 1
                else:
                    print_error(f"✗ {memory['memory_key']}: Creation failed")
            else:
                print_error(f"✗ {memory['memory_key']}: Status {response.status_code}")

        print_success(f"{success_count}/{len(memories)} memories created")
        return success_count == len(memories)

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_get_all_memories(access_token: str) -> bool:
    """Test GET /api/users/me/memories (list all memories)"""
    print_header("Test 3: Get All User Memories")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{API_URL}/api/users/me/memories",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"Request failed: Status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        memories = response.json()

        if not isinstance(memories, list):
            print_error(f"Expected list, got {type(memories)}")
            return False

        print_success(f"Retrieved {len(memories)} memories")

        # Display memories
        for memory in memories:
            print_info(f"  - {memory.get('memory_key')} ({memory.get('memory_type')})")
            print(f"    Value: {memory.get('memory_value')[:60]}...")
            print(f"    Importance: {memory.get('importance')}, Tags: {memory.get('tags')}")

        return len(memories) >= 4  # Should have at least 4 memories from previous tests

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_get_memory_by_key(access_token: str) -> bool:
    """Test GET /api/users/me/memories/{key} (get specific memory)"""
    print_header("Test 4: Get Memory by Key")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        memory_key = "favorite_character"

        response = requests.get(
            f"{API_URL}/api/users/me/memories/{memory_key}",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"Request failed: Status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        memory = response.json()

        if memory.get('memory_key') != memory_key:
            print_error(f"Expected key '{memory_key}', got '{memory.get('memory_key')}'")
            return False

        print_success(f"Retrieved memory: {memory_key}")
        print_info(f"Value: {memory.get('memory_value')}")
        print_info(f"Type: {memory.get('memory_type')}")
        print_info(f"Importance: {memory.get('importance')}")
        print_info(f"Tags: {memory.get('tags')}")
        print_info(f"Embedding: {'✓ Present' if memory.get('embedding') else '✗ Missing'}")

        return True

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_update_memory(access_token: str) -> bool:
    """Test PUT /api/users/me/memories/{key} (update memory)"""
    print_header("Test 5: Update Memory")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        memory_key = "favorite_character"

        update_data = {
            "memory_value": "렌고쿠와 탄지로를 모두 좋아한다. 두 사람 모두 강한 의지를 가졌다.",
            "importance": 0.95,  # Increased importance
            "tags": ["character", "preference", "rengoku", "tanjiro"]  # Added tanjiro tag
        }

        print_info(f"Updating: {memory_key}")
        print_info(f"New value: {update_data['memory_value'][:60]}...")

        response = requests.put(
            f"{API_URL}/api/users/me/memories/{memory_key}",
            headers=headers,
            json=update_data,
            timeout=30
        )

        if response.status_code != 200:
            print_error(f"Request failed: Status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        result = response.json()

        if not result.get('success'):
            print_error("Memory update failed")
            return False

        print_success(f"Memory updated: {memory_key}")
        print_info(f"Memory ID: {result.get('memory_id')}")

        # Verify update
        verify_response = requests.get(
            f"{API_URL}/api/users/me/memories/{memory_key}",
            headers=headers,
            timeout=10
        )

        if verify_response.status_code == 200:
            updated_memory = verify_response.json()
            print_success(f"Verified - Importance: {updated_memory.get('importance')}")
            print_success(f"Verified - Tags: {updated_memory.get('tags')}")
            return updated_memory.get('importance') == 0.95

        return True

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_semantic_search(access_token: str) -> bool:
    """Test POST /api/users/me/memories/search (vector similarity search)"""
    print_header("Test 6: Semantic Memory Search")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        search_queries = [
            {
                "query": "좋아하는 캐릭터",
                "description": "Search for favorite characters"
            },
            {
                "query": "친구 관계",
                "description": "Search for friendships"
            },
            {
                "query": "완료한 미션",
                "description": "Search for completed missions"
            }
        ]

        for search in search_queries:
            print_info(f"\nSearching: {search['description']}")
            print_info(f"Query: '{search['query']}'")

            response = requests.post(
                f"{API_URL}/api/users/me/memories/search",
                headers=headers,
                json={"query": search['query'], "limit": 3},
                timeout=30
            )

            if response.status_code != 200:
                print_warning(f"Search failed: {response.status_code}")
                continue

            results = response.json()

            if not isinstance(results, list):
                print_warning(f"Expected list, got {type(results)}")
                continue

            print_success(f"Found {len(results)} similar memories:")
            for i, memory in enumerate(results[:3], 1):
                distance = memory.get('distance', 'N/A')
                dist_str = f"{distance:.4f}" if isinstance(distance, float) else str(distance)
                print(f"  {i}. {memory.get('memory_key')} (distance: {dist_str})")
                print(f"     {memory.get('memory_value')[:60]}...")

        return True

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_delete_memory(access_token: str) -> bool:
    """Test DELETE /api/users/me/memories/{key} (soft delete)"""
    print_header("Test 7: Delete Memory")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        memory_key = "game_progress_train"

        print_info(f"Deleting: {memory_key}")

        response = requests.delete(
            f"{API_URL}/api/users/me/memories/{memory_key}",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            print_error(f"Request failed: Status {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        result = response.json()

        if not result.get('success'):
            print_error("Memory deletion failed")
            return False

        print_success(f"Memory deleted: {memory_key}")

        # Verify deletion (should return 404)
        verify_response = requests.get(
            f"{API_URL}/api/users/me/memories/{memory_key}",
            headers=headers,
            timeout=10
        )

        if verify_response.status_code == 404:
            print_success("Verified: Memory no longer accessible (soft deleted)")
            return True
        else:
            print_warning(f"Memory still accessible: Status {verify_response.status_code}")
            return False

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


def test_filter_by_type(access_token: str) -> bool:
    """Test filtering memories by type"""
    print_header("Test 8: Filter Memories by Type")

    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        memory_types = ["character_preference", "user_fact", "relationship"]

        for mem_type in memory_types:
            print_info(f"\nFiltering by type: {mem_type}")

            response = requests.get(
                f"{API_URL}/api/users/me/memories?memory_type={mem_type}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                print_warning(f"Request failed: {response.status_code}")
                continue

            memories = response.json()

            if not isinstance(memories, list):
                print_warning(f"Expected list, got {type(memories)}")
                continue

            print_success(f"Found {len(memories)} memories of type '{mem_type}'")
            for memory in memories:
                print(f"  - {memory.get('memory_key')}")

        return True

    except Exception as e:
        print_error(f"Exception: {e}")
        return False


# ============================================================
# Main Test Runner
# ============================================================

def main():
    """Run all E2E tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'🧪' * 35}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}     User Memory System E2E Testing Suite{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'🧪' * 35}{Colors.ENDC}\n")

    results = []

    # Register and login for authenticated tests
    print_header("User Registration & Authentication")
    access_token = register_and_login()

    if not access_token:
        print_error("Failed to get access token. Cannot proceed with tests.")
        return 1

    # Test 1: Create single memory
    results.append(("Create Memory", test_create_memory(access_token)))

    # Test 2: Create multiple memories
    results.append(("Create Multiple Memories", test_create_multiple_memories(access_token)))

    # Test 3: Get all memories
    results.append(("Get All Memories", test_get_all_memories(access_token)))

    # Test 4: Get specific memory
    results.append(("Get Memory by Key", test_get_memory_by_key(access_token)))

    # Test 5: Update memory
    results.append(("Update Memory", test_update_memory(access_token)))

    # Test 6: Semantic search
    results.append(("Semantic Search", test_semantic_search(access_token)))

    # Test 7: Delete memory
    results.append(("Delete Memory", test_delete_memory(access_token)))

    # Test 8: Filter by type
    results.append(("Filter by Type", test_filter_by_type(access_token)))

    # ============================================================
    # Test Results Summary
    # ============================================================

    print_header("Test Results Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{Colors.OKGREEN}✅ PASSED{Colors.ENDC}" if result else f"{Colors.FAIL}❌ FAILED{Colors.ENDC}"
        print(f"{status}  {test_name}")

    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.ENDC}")

    if passed == total:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 All tests passed! Memory system is working correctly.{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}⚠️  Some tests failed. Please review the errors above.{Colors.ENDC}\n")
        return 1

if __name__ == "__main__":
    exit(main())
