#!/usr/bin/env bash

echo "=== Stopping all normal clients ==="

for name in mqtt rest coap grpc; do
  pid_file="/tmp/${name}_client.pid"
  if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "Stopped ${name}_client PID $pid"
    else
      echo "${name}_client PID $pid is not running"
    fi
    rm -f "$pid_file"
  else
    echo "No PID file for ${name}_client"
  fi
done

echo "Done."
