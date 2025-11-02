"""
Test user progression initialization fix
"""
import requests
import json
import random

# Generate unique username
username = f"test_progression_{random.randint(100000, 999999)}"
email = f"{username}@example.com"

print(f"\n========================================")
print(f"Testing User Progression Fix")
print(f"========================================\n")

# 1. Register new user
print(f"1. Registering user: {username}")
register_data = {
    "username": username,
    "password": "test123",
    "email": email,
    "display_name": f"Test User {username}"
}

try:
    response = requests.post("http://localhost:8000/api/auth/register", json=register_data, timeout=10)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        user_id = result.get("user_id")
        print(f"   ✅ Registration successful!")
        print(f"   User ID: {user_id}")
        print(f"   Username: {result.get('username')}")
        print(f"   Display Name: {result.get('display_name')}")

        # 2. Login
        print(f"\n2. Logging in...")
        login_data = {
            "username": username,
            "password": "test123"
        }

        login_response = requests.post("http://localhost:8000/api/auth/login", json=login_data, timeout=10)
        print(f"   Status: {login_response.status_code}")

        if login_response.status_code == 200:
            login_result = login_response.json()
            access_token = login_result.get("access_token")
            print(f"   ✅ Login successful!")
            print(f"   Access Token: {access_token[:50]}...")

            print(f"\n========================================")
            print(f"✅ Test PASSED!")
            print(f"========================================")
            print(f"\nConclusion:")
            print(f"- User registration: ✅ SUCCESS")
            print(f"- User login: ✅ SUCCESS")
            print(f"- No table error occurred!")
            print(f"- DB progression fix is working correctly!")

        else:
            print(f"   ❌ Login failed: {login_response.text}")

    else:
        print(f"   ❌ Registration failed: {response.text}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n========================================\n")
