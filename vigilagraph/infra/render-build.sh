#!/bin/bash
set -e
pip install uv
cd apps/api && uv sync --no-dev
cd ../worker && uv sync --no-dev
