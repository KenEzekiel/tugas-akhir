#!/bin/bash

# Step 1: Start docker-compose services in eth2dgraph
cd eth2dgraph
docker-compose up -d alpha zero ratel

# Step 2: Start the Python API and MCP in a new terminal (or in background if no terminal available)
cd ..
cd system
if command -v gnome-terminal &> /dev/null; then
  gnome-terminal -- bash -c "python -m src.api.api; exec bash"
  gnome-terminal -- bash -c "python -m src.api.mcp; exec bash"
elif command -v x-terminal-emulator &> /dev/null; then
  x-terminal-emulator -e "bash -c 'python -m src.api.api; exec bash'" &
  x-terminal-emulator -e "bash -c 'python -m src.api.mcp; exec bash'" &
else
  # Fallback: run in background
  python -m src.api.api > ../logs/api.log 2>&1 &
  python -m src.api.mcp > ../logs/mcp.log 2>&1 &
  echo "Python API and MCP started in background. See api.log and mcp.log for output."
fi

# Step 3: Start the web dev server in a new terminal (or in background if no terminal available)
cd ..
cd web
if command -v gnome-terminal &> /dev/null; then
  gnome-terminal -- bash -c "npm run dev; exec bash"
elif command -v x-terminal-emulator &> /dev/null; then
  x-terminal-emulator -e "bash -c 'npm run dev; exec bash'" &
else
  # Fallback: run in background
  npm run dev > ../logs/web.log 2>&1 &
  echo "Web dev server started in background. See web.log for output."
fi

echo "All services started."
