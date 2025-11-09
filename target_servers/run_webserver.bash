#!/usr/bin/env bash

PORT=8080

echo "Starting Python web server on port $PORT..."
python3 -m http.server "$PORT" &
SERVER_PID=$!

echo "Server running with PID $SERVER_PID"
echo $SERVER_PID > server.pid
