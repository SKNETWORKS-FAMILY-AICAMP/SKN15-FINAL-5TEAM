#!/usr/bin/env python
"""
간단한 스테이지 진행 디버그 테스트
"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. 사용자 등록
        register_data = {
            "username": f"debugstage{int(asyncio.get_event_loop().time())}",
            "password": "test123",
            "full_name": "Debug Stage Test"
        }

        async with session.post(f"{BASE_URL}/api/auth/register", json=register_data) as resp:
            if resp.status not in [200, 201]:
                print(f"Registration failed: {await resp.text()}")
                return
            result = await resp.json()
            token = result["access_token"]
            print(f"✅ User registered: {register_data['username']}")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. 프롤로그 호출 (turn 0)
        chat_data = {
            "scenario_id": "mugen-train",
            "user_input": "",
            "user_name": register_data["username"]
        }

        async with session.post(f"{BASE_URL}/api/chat", json=chat_data, headers=headers) as resp:
            result = await resp.json()
            print(f"\n[Turn 0 - Prologue]")
            print(f"  Stage: {result.get('current_stage')}")
            print(f"  Dialogues: {len(result.get('dialogues', []))}")

        # 3-5. 3턴 대화 발송
        inputs = [
            "안녕하세요",
            "네, 괜찮아요",
            "계속할게요"
        ]

        for i, user_input in enumerate(inputs, start=1):
            chat_data["user_input"] = user_input
            async with session.post(f"{BASE_URL}/api/chat", json=chat_data, headers=headers) as resp:
                result = await resp.json()
                print(f"\n[Turn {i}]")
                print(f"  Input: {user_input}")
                print(f"  Stage: {result.get('current_stage')}")
                print(f"  turn_count: {result.get('turn_count')}")
                print(f"  Dialogues: {len(result.get('dialogues', []))}")

                if i == 3:
                    print(f"\n🔍 EXPECTED: Stage should be HEROES_ARRIVE (max_turns=3 reached)")
                    if result.get('current_stage') == "HEROES_ARRIVE":
                        print(f"✅ SUCCESS: Stage progression worked!")
                    else:
                        print(f"❌ FAILED: Still stuck at {result.get('current_stage')}")

if __name__ == "__main__":
    asyncio.run(main())
