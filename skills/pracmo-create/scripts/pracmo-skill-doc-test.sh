#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
skill="$root/SKILL.md"

for required in \
  "pracmo-learning-track@v1" \
  "learning-track.finalized.json" \
  "learning-tracks/import" \
  "learning-tracks/imports" \
  "512 KiB" \
  "不需要 API Key"; do
  rg -q "$required" "$skill" || { echo "missing skill contract: $required" >&2; exit 1; }
done

if rg -q "with-exercise|恰好一个练习|复用已有甲程" "$skill"; then
  echo "legacy instantaneous workflow remains in SKILL.md" >&2
  exit 1
fi

for file in \
  references/learning-track.schema.json \
  references/learning-track-json-contract.md \
  references/action-contract.md \
  scripts/validate_learning_track_json.py \
  scripts/compress_learning_track_images.py \
  scripts/finalize_learning_track_assets.py \
  scripts/learning_track_json_to_markdown.py \
  scripts/publish_learning_track.py; do
  test -f "$root/$file" || { echo "missing $file" >&2; exit 1; }
done

echo "pracmo skill doc tests passed"
