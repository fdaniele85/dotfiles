#!/bin/zsh

set -e

function usage() {
  echo "Usage: $0 input_dir max_minutes [--output-prefix PREFIX] [--start-date YYYY-MM-DD] [--dry-run]"
  exit 1
}

TRAPPED_FILES=()
TMP_FILES_TO_DELETE=()
function cleanup_on_exit() {
    for tmpf in "${TMP_FILES_TO_DELETE[@]}"; do
    [ -f "$tmpf" ] && rm "$tmpf"
    echo "🗑️  Cancellato $tmpf"
  done
}
function cleanup_on_interrupt() {
  for f in "${TRAPPED_FILES[@]}"; do
    [ -f "$f" ] && rm "$f"
    echo "🗑️  Cancellato $f"
  done
  cleanup_on_exit
  exit 1
}
trap cleanup_on_interrupt INT
trap cleanup_on_exit EXIT

[[ $# -lt 2 ]] && usage
INPUT_DIR="$1"
MAX_MINUTES="$2"
shift 2

START_DATE="$(date +%F)"
DRY_RUN=false
OUTPUT_PREFIX=""

zparseopts -D -E -output-prefix:=OUTPUT_PREFIX_OPT -start-date:=START_DATE_OPT -dry-run=DRY_OPT

if [[ -n "$OUTPUT_PREFIX_OPT" ]]; then
  OUTPUT_PREFIX="$OUTPUT_PREFIX_OPT[2]"
fi
if [[ -n "$START_DATE_OPT" ]]; then
  START_DATE="$START_DATE_OPT[2]"
fi
if [[ -n "$DRY_OPT" ]]; then
  DRY_RUN=true
fi

[[ ! -d "$INPUT_DIR" ]] && echo "Directory non trovata: $INPUT_DIR" && exit 1

BASENAME="$(basename "$INPUT_DIR")"
if [[ "$BASENAME" != *" - "* ]]; then
  echo "Il nome della directory deve essere nel formato 'autore - titolo'"
  exit 1
fi

ARTIST="${BASENAME%% - *}"
TITLE="${BASENAME##* - }"
[[ -z "$OUTPUT_PREFIX" ]] && OUTPUT_PREFIX="$TITLE"

COVER="$INPUT_DIR/cover.jpg"

cd "$INPUT_DIR"

MAX_MS=$((MAX_MINUTES * 60 * 1000))

MP3_FILES=(""*.mp3)

SILENCE_FILE="__silence_2s.mp3"
ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 2 -q:a 9 -acodec libmp3lame "$SILENCE_FILE" -y -loglevel quiet
TMP_FILES_TO_DELETE+="$SILENCE_FILE"

MP3_FILES=(${(on)MP3_FILES})  # Sort

INDEX=1
TMP_LIST="__concat_list.txt"
TMP_MERGE="__merged_output.mp3"
CURRENT_DATE="$START_DATE"

cat /dev/null > "$TMP_LIST"
TMP_FILES_TO_DELETE+="$TMP_LIST"
TMP_FILES_TO_DELETE+="$TMP_MERGE"

CURRENT_DURATION=0

TOTAL_FILES=${#MP3_FILES[@]}
i=1
print -n "\n📥 Lettura file MP3...\n"

for f in $MP3_FILES; do
  DUR_MS=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f" | awk '{printf("%d", $1 * 1000)}')
  
  print -n "\r🔄 [$i/$TOTAL_FILES] $f"
  ((i++))

  if [[ $DUR_MS -gt $MAX_MS ]]; then
    if [[ $CURRENT_DURATION -gt 0 ]]; then
      OUTFILE="${OUTPUT_PREFIX}_$(printf "%02d" $INDEX).mp3"
      if [[ "$DRY_RUN" == false ]]; then
        ffmpeg -f concat -safe 0 -i "$TMP_LIST" -c copy "$TMP_MERGE" -loglevel quiet
        mv "$TMP_MERGE" "$OUTFILE"
        mid3v2 -a "$ARTIST" -A "$TITLE" -t "$OUTFILE" -T "$INDEX" -y "$CURRENT_DATE" "$OUTFILE"
        [[ -f "$COVER" ]] && eyeD3 --add-image "$COVER":FRONT_COVER "$OUTFILE" > /dev/null
      fi
      DUR_MIN=$(((CURRENT_DURATION + 500) / 1000 / 60))
      echo "\r✅ Esportato $OUTFILE ($DUR_MIN min)"
      TRAPPED_FILES+="$OUTFILE"
      CURRENT_DATE=$(date -I -d "$CURRENT_DATE + 1 day")
      INDEX=$((INDEX + 1))
      cat /dev/null > "$TMP_LIST"
      CURRENT_DURATION=0
    fi

    OUTFILE="${OUTPUT_PREFIX}_$(printf "%02d" $INDEX).mp3"
    if [[ "$DRY_RUN" == false ]]; then
      cp "$f" "$OUTFILE"
      mid3v2 -a "$ARTIST" -A "$TITLE" -t "$OUTFILE" -T "$INDEX" -y "$CURRENT_DATE" "$OUTFILE"
      [[ -f "$COVER" ]] && eyeD3 --add-image "$COVER":FRONT_COVER "$OUTFILE" > /dev/null
    fi
    DUR_MIN=$(((DUR_MS + 500) / 1000 / 60))
    echo "\r✅ Esportato $OUTFILE (singolo file > max time) ($DUR_MIN min)"
    TRAPPED_FILES+="$OUTFILE"
    CURRENT_DATE=$(date -I -d "$CURRENT_DATE + 1 day")
    INDEX=$((INDEX + 1))
    continue
  fi

  ADD_DURATION=$DUR_MS
  if [[ $CURRENT_DURATION -gt 0 ]]; then
    ADD_DURATION=$((ADD_DURATION + 2000))
  fi

  if (( CURRENT_DURATION + ADD_DURATION > MAX_MS )); then
    OUTFILE="${OUTPUT_PREFIX}_$(printf "%02d" $INDEX).mp3"
    if [[ "$DRY_RUN" == false ]]; then
      ffmpeg -f concat -safe 0 -i "$TMP_LIST" -c copy "$TMP_MERGE" -loglevel quiet
      mv "$TMP_MERGE" "$OUTFILE"
      mid3v2 -a "$ARTIST" -A "$TITLE" -t "$OUTFILE" -T "$INDEX" -y "$CURRENT_DATE" "$OUTFILE"
      [[ -f "$COVER" ]] && eyeD3 --add-image "$COVER":FRONT_COVER "$OUTFILE" > /dev/null
    fi
    DUR_MIN=$(((CURRENT_DURATION + 500) / 1000 / 60))
    echo "\r✅ Esportato $OUTFILE ($DUR_MIN min)"
    TRAPPED_FILES+="$OUTFILE"
    CURRENT_DATE=$(date -I -d "$CURRENT_DATE + 1 day")
    INDEX=$((INDEX + 1))
    cat /dev/null > "$TMP_LIST"
    CURRENT_DURATION=0
  fi

  if [[ $CURRENT_DURATION -gt 0 ]]; then
    echo "file '$SILENCE_FILE'" >> "$TMP_LIST"
    CURRENT_DURATION=$((CURRENT_DURATION + 2000))
  fi

  echo "file '$f'" >> "$TMP_LIST"
  CURRENT_DURATION=$((CURRENT_DURATION + DUR_MS))
done

if [[ $CURRENT_DURATION -gt 0 ]]; then
  OUTFILE="${OUTPUT_PREFIX}_$(printf "%02d" $INDEX).mp3"
  if [[ "$DRY_RUN" == false ]]; then
    ffmpeg -f concat -safe 0 -i "$TMP_LIST" -c copy "$TMP_MERGE" -loglevel quiet
    mv "$TMP_MERGE" "$OUTFILE"
    mid3v2 -a "$ARTIST" -A "$TITLE" -t "$OUTFILE" -T "$INDEX" -y "$CURRENT_DATE" "$OUTFILE"
    [[ -f "$COVER" ]] && eyeD3 --add-image "$COVER":FRONT_COVER "$OUTFILE" > /dev/null
  fi
  DUR_MIN=$(((CURRENT_DURATION + 500) / 1000 / 60))
  echo "\n✅ Esportato $OUTFILE ($DUR_MIN min)"
  TRAPPED_FILES+="$OUTFILE"
fi

if [[ "$DRY_RUN" == false ]]; then
  mkdir -p originali_backup
  for f in $MP3_FILES; do
    mv "$f" "originali_backup/$f.bak"
  done
else
  for f in $MP3_FILES; do
    echo "[DRY-RUN] $f → originali_backup/$f.bak"
  done
fi

for tmpf in "${TMP_FILES_TO_DELETE[@]}"; do
  [ -f "$tmpf" ] && rm "$tmpf"
done

echo "\n🎉 Completato."
