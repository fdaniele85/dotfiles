#!/usr/bin/env zsh

zmodload zsh/datetime

PROGRESS_WIDTH="${PROGRESS_WIDTH:-32}"

typeset -a SOURCES
typeset -a FAILED_FILES
typeset -i TOTAL=0
typeset -i DONE=0
typeset -i FAILED=0
typeset -i START_TIME=0

format_duration() {
  local -i seconds="$1"
  local -i hours minutes

  (( seconds < 0 )) && seconds=0
  hours=$(( seconds / 3600 ))
  minutes=$(( (seconds % 3600) / 60 ))
  seconds=$(( seconds % 60 ))

  printf "%02d:%02d:%02d" "$hours" "$minutes" "$seconds"
}

estimate_eta() {
  local -i done="$1"
  local -i total="$2"
  local -i elapsed="$3"
  local -i remaining eta

  if (( done == 0 )); then
    printf "%s" "--:--:--"
    return
  fi

  remaining=$(( total - done ))
  eta=$(( elapsed * remaining / done ))
  format_duration "$eta"
}

render_progress() {
  local -i done="$1"
  local -i total="$2"
  local -i start_time="$3"
  local -i now elapsed filled percent i
  local bar elapsed_text eta_text

  now="$EPOCHSECONDS"
  elapsed=$(( now - start_time ))

  if (( total > 0 )); then
    filled=$(( done * PROGRESS_WIDTH / total ))
    percent=$(( done * 100 / total ))
  else
    filled=0
    percent=100
  fi

  bar=""
  for (( i = 0; i < filled; i++ )); do
    bar+="#"
  done
  for (( i = filled; i < PROGRESS_WIDTH; i++ )); do
    bar+="-"
  done

  elapsed_text="$(format_duration "$elapsed")"
  eta_text="$(estimate_eta "$done" "$total" "$elapsed")"

  printf "\r[%s] %3d%%  %d/%d  elapsed %s  ETA %s" \
    "$bar" "$percent" "$done" "$total" "$elapsed_text" "$eta_text"
}

collect_sources() {
  local -a dirs
  local dir source

  if (( $# == 0 )); then
    dirs=(.)
  else
    dirs=("$@")
  fi

  for dir in "$dirs[@]"; do
    if [[ ! -d "$dir" ]]; then
      print -u2 -- "Skipping '$dir' (not a directory)"
      continue
    fi

    for source in "$dir"/*.flac(N); do
      SOURCES+=("$source")
    done
  done
}

convert_file() {
  local source="$1"
  local target="${source:r}.mp3"
  local error_log="$2"

  print -r -- "== $source ==" >> "$error_log"

  ffmpeg \
    -hide_banner \
    -nostdin \
    -loglevel error \
    -y \
    -i "$source" \
    -vn \
    -q:a 0 \
    -map_metadata 0 \
    -id3v2_version 3 \
    -write_id3v1 1 \
    "$target" \
    >> "$error_log" 2>&1
}

run_conversion() {
  local source="$1"
  local error_log="$2"
  local -i pid exit_code

  convert_file "$source" "$error_log" &
  pid=$!

  while kill -0 "$pid" 2>/dev/null; do
    render_progress "$DONE" "$TOTAL" "$START_TIME"
    sleep 1
  done

  wait "$pid"
  exit_code=$?

  if (( exit_code == 0 )); then
    rm -f -- "$source"
  else
    FAILED_FILES+=("$source")
    (( FAILED++ ))
  fi

  (( DONE++ ))
  render_progress "$DONE" "$TOTAL" "$START_TIME"
}

main() {
  local source error_log

  collect_sources "$@"
  TOTAL="${#SOURCES[@]}"

  if (( TOTAL == 0 )); then
    print -- "No FLAC files found."
    return 0
  fi

  error_log="$(mktemp "${TMPDIR:-/tmp}/flac-to-mp3.XXXXXX")" || return 1
  trap 'rm -f -- "$error_log"' EXIT

  START_TIME="$EPOCHSECONDS"
  render_progress 0 "$TOTAL" "$START_TIME"

  for source in "$SOURCES[@]"; do
    run_conversion "$source" "$error_log"
  done

  print

  if (( FAILED > 0 )); then
    print -u2 -- "Failed conversions: $FAILED/$TOTAL"
    for source in "$FAILED_FILES[@]"; do
      print -u2 -- "  $source"
    done
    print -u2 -- "ffmpeg error log: $error_log"
    trap - EXIT
    return 1
  fi

  return 0
}

main "$@"
