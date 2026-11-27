#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export NIGHT_NINE_SAVE_DIR="$PROJECT_ROOT/tmp/qa"
mkdir -p "$NIGHT_NINE_SAVE_DIR"
AUDIO_ARGUMENTS=(--max-fps 60)
if [[ -n "${NIGHT_NINE_QA_AUDIO_DRIVER:-}" ]]; then
  AUDIO_ARGUMENTS+=(--audio-driver "$NIGHT_NINE_QA_AUDIO_DRIVER")
  echo "QA audio driver: $NIGHT_NINE_QA_AUDIO_DRIVER"
fi
bash "$PROJECT_ROOT/tools/godot.sh" --headless --editor --import --quit --log-file "$NIGHT_NINE_SAVE_DIR/campaign-import.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/campaign-import.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --script res://tests/test_campaign.gd --log-file "$NIGHT_NINE_SAVE_DIR/campaign-core.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/campaign-core.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_story_runtime_fixes.gd --log-file "$NIGHT_NINE_SAVE_DIR/story-runtime-fixes.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/story-runtime-fixes.log"
(cd "$PROJECT_ROOT/tools" && python3 -m unittest test_story_runtime_sources.py)
bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_broadcast_desk.gd --log-file "$NIGHT_NINE_SAVE_DIR/broadcast-desk.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/broadcast-desk.log"
CHAPTER_QA="$NIGHT_NINE_SAVE_DIR/chapter-replay-$$"
mkdir -p "$CHAPTER_QA"
NIGHT_NINE_SAVE_DIR="$CHAPTER_QA/save" NIGHT_NINE_QA_DIR="$CHAPTER_QA" bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_chapter_replay.gd --log-file "$CHAPTER_QA/chapter-replay.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$CHAPTER_QA/chapter-replay.log"
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$CHAPTER_QA/chapter-replay-results.json" 20
bash "$PROJECT_ROOT/tools/godot.sh" --headless --script res://tests/test_exploration_floor.gd --log-file "$NIGHT_NINE_SAVE_DIR/exploration-floor.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/exploration-floor.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_physical_navigation.gd --log-file "$NIGHT_NINE_SAVE_DIR/physical-navigation.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/physical-navigation.log"
NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_SAVE_DIR/walking-input" bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_exploration_input.gd --log-file "$NIGHT_NINE_SAVE_DIR/exploration-input.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/exploration-input.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --script res://tests/test_tape_recording.gd --log-file "$NIGHT_NINE_SAVE_DIR/tape-core.log" 2>&1 | tee "$NIGHT_NINE_SAVE_DIR/tape-core-console.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/tape-core.log" "$NIGHT_NINE_SAVE_DIR/tape-core-console.log"
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$PROJECT_ROOT/tmp/qa/tape-recording-results.json" 51
bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script res://tests/test_investigation_puzzles.gd --log-file "$NIGHT_NINE_SAVE_DIR/investigation-puzzles.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/investigation-puzzles.log"
bash "$PROJECT_ROOT/tools/godot.sh" --headless --script res://tests/test_voice_assets.gd --log-file "$NIGHT_NINE_SAVE_DIR/voice-assets.log" 2>&1 | tee "$NIGHT_NINE_SAVE_DIR/voice-assets-console.log"
python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/voice-assets.log" "$NIGHT_NINE_SAVE_DIR/voice-assets-console.log"
export NIGHT_NINE_QA_DIR="$PROJECT_ROOT/tmp/qa/extended-run-$$"
mkdir -p "$NIGHT_NINE_QA_DIR"
for SUITE in animation_handoff campaign_music case_boards social_staging small_talk story_staging bay_receiver; do
  NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/$SUITE-save" bash "$PROJECT_ROOT/tools/godot.sh" --headless --audio-driver Dummy --script "res://tests/test_$SUITE.gd" --log-file "$NIGHT_NINE_QA_DIR/$SUITE.log"
  python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_QA_DIR/$SUITE.log"
done
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/animation-handoff.json" 10
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/score-route.json" 404
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/case-boards.json" 716
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/social-staging.json" 152
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/small-talk.json" 345
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/story-staging.json" 550
python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/bay-receiver.json" 24
if [[ "${1:-}" == "--render" ]]; then
  export NIGHT_NINE_QA_DIR="$PROJECT_ROOT/tmp/qa/campaign-run-$$"
  mkdir -p "$NIGHT_NINE_QA_DIR"
  NIGHT_NINE_QA_EXPECT_V4="${NIGHT_NINE_QA_EXPECT_V4:-0}" NIGHT_NINE_QA_EXPECT_INSERTS="${NIGHT_NINE_QA_EXPECT_INSERTS:-1}" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --quit-after 60000 --log-file "$NIGHT_NINE_SAVE_DIR/campaign-render.log" -- --campaign-qa 2>&1 | tee "$NIGHT_NINE_SAVE_DIR/campaign-render-console.log"
  python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_SAVE_DIR/campaign-render.log" "$NIGHT_NINE_SAVE_DIR/campaign-render-console.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/campaign-render/results.json" 6284
  NIGHT_NINE_SAVE_DIR="$PROJECT_ROOT/tmp/qa/input-save" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --quit-after 1200 --log-file "$PROJECT_ROOT/tmp/qa/campaign-input.log" -- --campaign-input-qa 2>&1 | tee "$PROJECT_ROOT/tmp/qa/campaign-input-console.log"
  python3 "$PROJECT_ROOT/tools/check-log.py" "$PROJECT_ROOT/tmp/qa/campaign-input.log" "$PROJECT_ROOT/tmp/qa/campaign-input-console.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/campaign-input-results.json" 31
  NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/prologue-save" NIGHT_NINE_QA_DIR="$NIGHT_NINE_QA_DIR/prologue" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --quit-after 7200 --log-file "$PROJECT_ROOT/tmp/qa/illustrated-prologue.log" -- --illustrated-prologue-qa
  python3 "$PROJECT_ROOT/tools/check-log.py" "$PROJECT_ROOT/tmp/qa/illustrated-prologue.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/prologue/prologue-gameplay.json" 169
  NIGHT_NINE_QA_MINIMIZE=1 NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/story-save" NIGHT_NINE_QA_DIR="$NIGHT_NINE_QA_DIR/story" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --log-file "$PROJECT_ROOT/tmp/qa/story-flow.log" -- --story-qa
  python3 "$PROJECT_ROOT/tools/check-log.py" "$PROJECT_ROOT/tmp/qa/story-flow.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/story/story-flow.json" 90
  NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/tape-save" NIGHT_NINE_QA_DIR="$NIGHT_NINE_QA_DIR/tape" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --quit-after 1800 --log-file "$PROJECT_ROOT/tmp/qa/tape-render.log" -- --tape-qa 2>&1 | tee "$PROJECT_ROOT/tmp/qa/tape-render-console.log"
  python3 "$PROJECT_ROOT/tools/check-log.py" "$PROJECT_ROOT/tmp/qa/tape-render.log" "$PROJECT_ROOT/tmp/qa/tape-render-console.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/tape/tape-results.json" 39
  for SUITE in case_boards social_staging; do
    NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/$SUITE-save" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --script "res://tests/test_$SUITE.gd" --log-file "$NIGHT_NINE_QA_DIR/$SUITE.log"
    python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_QA_DIR/$SUITE.log"
  done
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/case-boards.json" 716
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/social-staging.json" 152
  NIGHT_NINE_SAVE_DIR="$NIGHT_NINE_QA_DIR/staging-save" NIGHT_NINE_QA_DIR="$NIGHT_NINE_QA_DIR/staging" bash "$PROJECT_ROOT/tools/godot.sh" "${AUDIO_ARGUMENTS[@]}" --quit-after 3600 --log-file "$NIGHT_NINE_QA_DIR/staging.log" -- --staging-qa
  python3 "$PROJECT_ROOT/tools/check-log.py" "$NIGHT_NINE_QA_DIR/staging.log"
  python3 "$PROJECT_ROOT/tools/check-qa-result.py" "$NIGHT_NINE_QA_DIR/staging/staging-results.json" 133
  python3 - "$NIGHT_NINE_QA_DIR" "$PROJECT_ROOT/tmp/qa" <<'PY'
import shutil,sys
shutil.copytree(sys.argv[1],sys.argv[2],dirs_exist_ok=True)
PY
fi
