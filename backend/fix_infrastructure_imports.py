#!/usr/bin/env python3
"""
Fix Infrastructure layer relative imports to absolute imports
"""
import os
import re

# Files that need fixing (from verification script)
FILES_TO_FIX = [
    "src/infrastructure/database/connection.py",
    "src/infrastructure/database/repositories/postgres_user_repository.py",
    "src/infrastructure/database/repositories/postgres_session_repository.py",
    "src/infrastructure/database/session_manager.py",
    "src/infrastructure/database/session_manager_adapter.py",
    "src/infrastructure/database/db_manager.py",
    "src/infrastructure/cache/cache_manager.py",
    "src/infrastructure/cache/redis_connection.py",
    "src/infrastructure/cache/redis_cache_provider.py",
    "src/infrastructure/cache/strategies/session_cache_strategy.py",
    "src/infrastructure/llm/providers/openai_llm_provider.py",
    "src/infrastructure/persistence/postgresql/repositories/character_repo.py",
]

def fix_imports_in_file(filepath):
    """Fix relative imports to absolute imports in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace relative imports with absolute imports
        # Pattern 1: from core.* → from src.core.*
        content = re.sub(
            r'^from core\.',
            'from src.core.',
            content,
            flags=re.MULTILINE
        )

        # Pattern 2: from infrastructure.* → from src.infrastructure.*
        content = re.sub(
            r'^from infrastructure\.',
            'from src.infrastructure.',
            content,
            flags=re.MULTILINE
        )

        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {filepath}")
            return True
        else:
            print(f"⏭️  Skipped (no changes): {filepath}")
            return False

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

def main():
    """Main function"""
    base_dir = "/Users/kwondowon/Downloads/myproject55/backend"

    fixed_count = 0
    skipped_count = 0
    error_count = 0

    print("=" * 60)
    print("🔧 Fixing Infrastructure Layer Relative Imports")
    print("=" * 60)

    for file_path in FILES_TO_FIX:
        full_path = os.path.join(base_dir, file_path)

        if not os.path.exists(full_path):
            print(f"⚠️  File not found: {file_path}")
            error_count += 1
            continue

        result = fix_imports_in_file(full_path)
        if result:
            fixed_count += 1
        else:
            skipped_count += 1

    print("\n" + "=" * 60)
    print(f"✅ Fixed: {fixed_count} files")
    print(f"⏭️  Skipped: {skipped_count} files")
    print(f"❌ Errors: {error_count} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
