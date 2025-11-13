#!/usr/bin/env python3
"""
Context Fix Verification Script

This script explains the fix and what to verify:

## Problem:
- `get_all_previous_stage_tags()` was returning [] (empty list)
- Reason: scenario_data was not being added to session_state
- Result: No previous stage context, causing dialogue inconsistencies

## Fix Applied:
File: backend/app/features/chat/usecase.py (lines 582-590)
- Added scenario_data loading before ParentAgent.run()
- scenario_data is now included in session_state

## What to Verify:
1. Start a NEW chat session (old sessions won't show the fix)
2. Progress through multiple stages:
   - TRAIN_PRELUDE
   - HEROES_ARRIVE  
   - USER_INTRODUCTION

3. Check logs for:
   ```
   🔍 INPUT: current_stage_tag=HEROES_ARRIVE, scenario keys=[...]
   🔍 Previous stages: ['TRAIN_PRELUDE']
   ```

4. Check that at USER_INTRODUCTION:
   ```
   🔍 Previous stages: ['TRAIN_PRELUDE', 'HEROES_ARRIVE']
   🔍 Prologue: 3, Previous: X, Current: Y
   ```
   (Previous should be > 0)

5. Verify dialogue quality:
   - Characters remember previous conversations
   - No world-breaking content (modern concepts in Taisho era)
   - Natural conversation flow

## How to Check Logs:
docker-compose logs backend 2>&1 | grep -A 5 "get_all_previous_stage_tags\|collect_recent_dialogues" | tail -50
"""

print(__doc__)
