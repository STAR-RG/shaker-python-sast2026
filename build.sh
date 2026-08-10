#!/bin/bash
set -e

echo "==> Building shaker/shaker-image..."
docker build -f docker/Dockerfile -t shaker/shaker-image .
echo "==> Build complete."
