#!/bin/bash

# Stop docker-compose services in eth2dgraph
cd eth2dgraph
docker-compose down

# Stop Python API and MCP processes
cd ../system

# Find and kill the Python API process by matching the full command line
API_PIDS=$(ps aux | grep '[P]ython.*-m src.api.api' | awk '{print $2}')
if [ -n "$API_PIDS" ]; then
  for PID in $API_PIDS; do
    if kill "$PID" 2>/dev/null; then
      echo "Stopped Python API (PID $PID)"
    else
      echo "Python API process $PID was not running"
    fi
  done
else
  echo "Python API not running"
fi

# Find and kill the MCP process by matching the full command line
MCP_PIDS=$(ps aux | grep '[P]ython.*-m src.api.mcp' | awk '{print $2}')
if [ -n "$MCP_PIDS" ]; then
  for PID in $MCP_PIDS; do
    if kill "$PID" 2>/dev/null; then
      echo "Stopped MCP (PID $PID)"
    else
      echo "MCP process $PID was not running"
    fi
  done
else
  echo "MCP not running"
fi

# Stop the web dev server
cd ../web

# Try to find and kill the npm run dev process
WEB_PID=$(ps aux | grep '[n]pm run dev' | awk '{print $2}')
if [ -n "$WEB_PID" ]; then
  kill $WEB_PID
  echo "Stopped web dev server (PID $WEB_PID)"
else
  echo "Web dev server not running"
fi

echo "All services stopped."
