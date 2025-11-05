#!/usr/bin/env python3
"""
Script to restructure JSON beats to be dialogue-centered instead of narration-heavy.
"""
import json
import re

def restructure_beat(beat):
    """
    Convert a narration-heavy beat to dialogue-centered.
    """
    goal = beat.get("goal", "")

    # Pattern 1: Direct speech already exists - extract it
    # Example: "렌고쿠가 외친다. '불꽃이여!'" -> "렌고쿠: '불꽃이여!'"
    pattern1 = r"(.+?)(가|이|는|께서)\s+(말한다|외친다|속삭인다|묻는다|대답한다|설명한다|소개한다|칭찬한다|자랑한다|조소한다|비웃는다|절규한다|중얼거린다|당부한다)[\.]\s+'(.+?)'"
    match1 = re.search(pattern1, goal)
    if match1:
        speaker = match1.group(1)
        speech = match1.group(4)
        beat["goal"] = f"{speaker}: '{speech}'"
        return beat

    # Pattern 2: Indirect speech with quotes
    # Example: "렌고쿠가 '우마이!'를 외친다" -> "렌고쿠: '우마이!'"
    pattern2 = r"(.+?)(가|이|는|께서)\s+'(.+?)'(를|을|라고|라며|며|고).+"
    match2 = re.search(pattern2, goal)
    if match2:
        speaker = match2.group(1)
        speech = match2.group(3)
        beat["goal"] = f"{speaker}: '{speech}'"
        return beat

    # Pattern 3: Remove unnecessary descriptive phrases for narr
    if "speaker_hint" in beat and "narr" in beat["speaker_hint"]:
        # Remove verbose transitions
        goal = re.sub(r"【.+?】\s*", "", goal)  # Remove 【엔무전 직후】 etc
        goal = re.sub(r"(열차|객차|전장).+(멈추고|흐르고).+?\.", "", goal)
        goal = re.sub(r"(.+?)(가|이)\s+(달려와|쓰러지며|비틀거리며|무너지며)\s+", r"\1\2 ", goal)
        beat["goal"] = goal.strip()

    return beat


def process_beats_section(beats_list):
    """Process a list of beats."""
    return [restructure_beat(beat) for beat in beats_list]


def main():
    # Read the JSON file
    with open("/Users/kwondowon/Downloads/kime_chat_agent/backend/data/scenarios/cutscene5_llm_driven.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Process all beats in i18n.ko
    i18n_ko = data.get("i18n", {}).get("ko", {})

    for key in i18n_ko:
        if key.startswith("beats_"):
            print(f"Processing {key}...")
            i18n_ko[key] = process_beats_section(i18n_ko[key])

    # Write back
    with open("/Users/kwondowon/Downloads/kime_chat_agent/backend/data/scenarios/cutscene5_llm_driven_restructured.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Done! Output written to cutscene5_llm_driven_restructured.json")


if __name__ == "__main__":
    main()
