#!/usr/bin/env python3
"""
Fix syntax errors in route files - remove incorrect indentation
"""
import os
import re

FILES_TO_FIX = [
    "src/application/routes/leaderboard_routes.py",
    "src/application/routes/system_routes.py",
    "src/application/routes/session_routes.py",
    "src/application/routes/memories_routes.py",
    "src/application/routes/scenario_routes.py",
]

def fix_file(filepath):
    """Fix indentation issues in imports"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        fixed_lines = []
        in_import_section = False
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            # Detect incorrect indentation in imports (starts with 4+ spaces and 'from')
            if re.match(r'^\s{4,}from ', line):
                # Remove indentation
                fixed_line = line.lstrip()
                fixed_lines.append(fixed_line)
                in_import_section = True
            # Check for leftover try/except blocks from previous cleanup
            elif 'except ModuleNotFoundError:' in line and in_import_section:
                # Skip this line and the next import line
                skip_next = True
                continue
            else:
                fixed_lines.append(line)
                # Reset import section flag if we see non-import line
                if not line.strip().startswith(('from', 'import', '#')) and line.strip():
                    in_import_section = False

        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)

        print(f"✅ Fixed: {filepath}")
        return True

    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

def main():
    """Main function"""
    base_dir = "/Users/kwondowon/Downloads/myproject55/backend"

    print("=" * 60)
    print("🔧 Fixing Route Files Syntax Errors")
    print("=" * 60)

    fixed_count = 0
    for file_path in FILES_TO_FIX:
        full_path = os.path.join(base_dir, file_path)

        if not os.path.exists(full_path):
            print(f"⚠️  File not found: {file_path}")
            continue

        if fix_file(full_path):
            fixed_count += 1

    print("\n" + "=" * 60)
    print(f"✅ Fixed: {fixed_count}/{len(FILES_TO_FIX)} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
