#!/usr/bin/env python3
"""
Comprehensive Import Validation
Checks all Python files in src/ can be compiled without syntax errors
"""
import os
import sys
import py_compile
from pathlib import Path

def validate_file(filepath):
    """Validate a single Python file"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main validation function"""
    base_dir = Path("/Users/kwondowon/Downloads/myproject55/backend/src")

    print("=" * 70)
    print("🔍 Comprehensive Import Validation")
    print("=" * 70)

    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                all_files.append(os.path.join(root, file))

    all_files.sort()

    success_count = 0
    error_count = 0
    errors = []

    print(f"\n📊 Found {len(all_files)} Python files\n")

    for filepath in all_files:
        rel_path = os.path.relpath(filepath, base_dir.parent)
        success, error_msg = validate_file(filepath)

        if success:
            success_count += 1
            print(f"✅ {rel_path}")
        else:
            error_count += 1
            errors.append((rel_path, error_msg))
            print(f"❌ {rel_path}")

    print("\n" + "=" * 70)
    print(f"✅ Success: {success_count}/{len(all_files)} files")
    print(f"❌ Errors: {error_count}/{len(all_files)} files")
    print("=" * 70)

    if errors:
        print("\n🔴 Files with errors:\n")
        for filepath, error_msg in errors:
            print(f"❌ {filepath}")
            print(f"   {error_msg}\n")
        return 1
    else:
        print("\n🎉 All files passed validation!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
