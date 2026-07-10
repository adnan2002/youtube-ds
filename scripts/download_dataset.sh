#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$repo_root/data/raw" "$repo_root/data/processed"

curl -L -o "$repo_root/data/raw/youtube-trending-videos-dataset.zip" \
  https://www.kaggle.com/api/v1/datasets/download/thedevastator/youtube-trending-videos-dataset
