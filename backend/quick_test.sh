#!/bin/bash
echo "1
테스트" | python play.py 2>&1 | head -100
