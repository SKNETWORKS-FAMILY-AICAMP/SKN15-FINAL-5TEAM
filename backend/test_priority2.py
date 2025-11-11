"""
우선순위 2 기능 테스트
- ConversationSummarizer
- Memory 저장
- pgvector 유사도 검색
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.embeddings import get_embeddings_service
from app.features.memories.repository import MemoriesRepository
from app.features.memories.models import UserMemory
import os


async def test_memory_system():
    """Memory 시스템 테스트"""
    print("=" * 60)
    print("🧪 Memory System Test")
    print("=" * 60)

    # Database connection
    db_url = "postgresql+asyncpg://kime:dev123@localhost:5432/kimedb"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = MemoriesRepository(session)
        embeddings_service = get_embeddings_service()

        # 테스트 사용자 ID
        test_user_id = "9283bf4c-09d6-4685-ae40-232cb5a47e3e"  # demo user

        print("\n1️⃣ 테스트 기억 생성 중...")

        # 테스트 기억 데이터
        test_memories = [
            {
                "content": "탄지로와 처음 만났을 때, 그는 매우 친절하게 인사했다. 따뜻한 미소가 인상적이었다.",
                "memory_type": "episodic",
                "scenario_id": "mugen-train"
            },
            {
                "content": "렌고쿠는 강한 불꽃 호흡을 사용하는 염주다. 정의감이 넘치고 동료를 아끼는 성격이다.",
                "memory_type": "semantic",
                "scenario_id": "mugen-train"
            },
            {
                "content": "무한열차에서 하현의 일 엔무를 만났다. 악몽을 보는 혈귀술을 사용했다.",
                "memory_type": "episodic",
                "scenario_id": "mugen-train"
            }
        ]

        # 임베딩 생성 및 저장
        created_memories = []
        for mem_data in test_memories:
            try:
                # 임베딩 생성
                embedding = embeddings_service.embed(mem_data["content"])

                # Memory 저장
                memory = await repo.create_memory(
                    user_id=test_user_id,
                    content=mem_data["content"],
                    memory_type=mem_data["memory_type"],
                    embedding=embedding,
                    scenario_id=mem_data["scenario_id"],
                    importance_score=0.8
                )
                created_memories.append(memory)
                print(f"   ✅ Memory {memory.memory_id} 생성: {mem_data['content'][:40]}...")

            except Exception as e:
                print(f"   ❌ 실패: {e}")

        await session.commit()

        print(f"\n✅ {len(created_memories)}개 기억 생성 완료")

        # 2. 유사도 검색 테스트
        print("\n2️⃣ 유사도 검색 테스트...")

        query_text = "탄지로는 어떤 사람인가요?"
        print(f"   질문: {query_text}")

        try:
            # 쿼리 임베딩 생성
            query_embedding = embeddings_service.embed(query_text)

            # 유사 기억 검색
            similar_memories = await repo.search_similar_memories(
                query_embedding=query_embedding,
                user_id=test_user_id,
                limit=3,
                similarity_threshold=0.5
            )

            print(f"\n   📚 찾은 기억 ({len(similar_memories)}개):")
            for i, mem in enumerate(similar_memories, 1):
                print(f"   {i}. [{mem['memory_type']}] 유사도: {mem['similarity']:.3f}")
                print(f"      {mem['content'][:80]}...")

        except Exception as e:
            print(f"   ❌ 검색 실패: {e}")

        # 3. 사용자 기억 조회
        print("\n3️⃣ 사용자 전체 기억 조회...")

        try:
            all_memories = await repo.get_user_memories(
                user_id=test_user_id,
                scenario_id="mugen-train",
                limit=10
            )

            print(f"   📖 총 {len(all_memories)}개 기억 보유")
            for mem in all_memories[:5]:
                print(f"   - [{mem.memory_type}] {mem.content[:50]}...")

        except Exception as e:
            print(f"   ❌ 조회 실패: {e}")

        print("\n" + "=" * 60)
        print("✅ 테스트 완료!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_memory_system())
