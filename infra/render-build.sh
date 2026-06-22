#!/bin/bash
set -e
pip install uv
cd api && uv sync --no-dev
