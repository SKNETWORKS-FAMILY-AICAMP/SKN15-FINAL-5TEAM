#!/usr/bin/env python3
import os
import re

taemin_record_dir = "/Users/jtm427/Desktop/workspace/taemin_record"

for filename in sorted(os.listdir(taemin_record_dir)):
    if filename.endswith(".md"):
        filepath = os.path.join(taemin_record_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                # 첫 줄에 영어 단어가 많으면 영어로 간주
                if first_line.startswith('#'):
                    title = first_line.lstrip('#').strip()
                    # 영어 알파벳이 한글보다 많으면 영어 문서
                    english_count = len(re.findall(r'[A-Za-z]', title))
                    korean_count = len(re.findall(r'[가-힣]', title))

                    if english_count > korean_count and english_count > 5:
                        print(f"🔴 영어: {filename}")
                        print(f"   제목: {title}")
                    else:
                        print(f"✅ 한글: {filename}")
        except Exception as e:
            print(f"❌ 오류: {filename} - {e}")
