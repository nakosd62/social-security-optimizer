#!/bin/bash

# cd ~/Coding/social-security-optimizer
# python3 -m venv .venv
source .venv/bin/activate
# pip install -r requirements.txt

PID=$(lsof -ti tcp:5000 -sTCP:LISTEN)
if [ -n "$PID" ]; then
  kill $PID
  sleep 1
  kill -0 $PID 2>/dev/null && kill -9 $PID   # force it if it's still alive
fi

nohup python3 -u main.py > main.log 2>&1 &