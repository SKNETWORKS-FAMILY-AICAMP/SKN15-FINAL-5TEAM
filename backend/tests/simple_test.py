#!/usr/bin/env python3
"""
간단한 통합 테스트 - 기본 기능 확인
"""
import sys
sys.path.insert(0, '.')

def test_imports():
    """모든 핵심 모듈 임포트 테스트"""
    print("📦 모듈 임포트 테스트...\n")

    try:
        from parent_agent_enhanced import ParentAgent
        print("✅ Parent Agent")

        from children_agent_enhanced import ChildrenAgent
        print("✅ Children Agent")

        from router_agent_enhanced import RouterAgent
        print("✅ Router Agent")

        from guardrail_agent_enhanced import GuardrailAgent
        print("✅ Guardrail Agent")

        from langgraph_workflow import get_workflow
        print("✅ LangGraph Workflow")

        print("\n🎉 모든 모듈 임포트 성공!\n")
        return True

    except Exception as e:
        print(f"\n❌ 임포트 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_config_loading():
    """설정 파일 로드 테스트"""
    print("⚙️  설정 파일 로드 테스트...\n")

    try:
        import json
        from pathlib import Path

        # Parent config
        parent_config = Path("config/parent_config.json")
        if parent_config.exists():
            with open(parent_config, 'r') as f:
                data = json.load(f)
                print(f"✅ Parent Config: {data.get('main_guide_character')}")
        else:
            print("⚠️  Parent Config 없음 (기본값 사용)")

        # Characters DB
        char_db = Path("data/characters_db.json")
        if char_db.exists():
            with open(char_db, 'r') as f:
                data = json.load(f)
                chars = data.get("characters", {})
                print(f"✅ Characters DB: {len(chars)}개 캐릭터")

                # 페르소나 확인
                for char_id in ["tanjiro", "inosuke", "zenitsu", "rengoku"]:
                    char_data = chars.get(char_id, {})
                    if "persona" in char_data:
                        print(f"   - {char_id}: 페르소나 ✓")
                    else:
                        print(f"   - {char_id}: 페르소나 ✗")

        print("\n🎉 설정 파일 로드 성공!\n")
        return True

    except Exception as e:
        print(f"\n❌ 설정 로드 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_hardcoding_removal():
    """하드코딩 제거 확인"""
    print("🧹 하드코딩 제거 확인...\n")

    try:
        # Parent Agent 인스턴스 생성
        from parent_agent_enhanced import ParentAgent
        parent = ParentAgent(use_llm=False, debug=False)

        # Config 로드 확인
        if hasattr(parent, 'config'):
            print(f"✅ Parent Agent config 로드: {parent.config.get('main_guide_character')}")
        else:
            print("❌ Parent Agent config 없음")
            return False

        # Children Agent 인스턴스 생성
        from children_agent_enhanced import ChildrenAgent
        children = ChildrenAgent(use_llm=False, debug=False)

        # 캐릭터 DB에서 페르소나 로드 확인
        test_char = children.characters_data.get("tanjiro", {})
        if "persona" in test_char:
            persona = test_char["persona"]
            print(f"✅ Children Agent - Tanjiro 페르소나:")
            print(f"   Core Traits: {persona.get('core_traits', '')[:50]}...")
            print(f"   Speech Patterns: {', '.join(persona.get('speech_patterns', [])[:3])}")
        else:
            print("❌ Children Agent - 페르소나 없음")
            return False

        print("\n🎉 하드코딩 제거 확인 완료!\n")
        return True

    except Exception as e:
        print(f"\n❌ 하드코딩 확인 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*80)
    print("🧪 통합 테스트 Suite")
    print("="*80 + "\n")

    results = []

    # 1. 임포트 테스트
    results.append(("모듈 임포트", test_imports()))

    # 2. 설정 로드 테스트
    results.append(("설정 파일 로드", test_config_loading()))

    # 3. 하드코딩 제거 확인
    results.append(("하드코딩 제거", test_hardcoding_removal()))

    # 결과 요약
    print("="*80)
    print("📊 테스트 결과 요약")
    print("="*80)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(success for _, success in results)

    print("="*80)
    if all_passed:
        print("🎉 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("="*80 + "\n")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
