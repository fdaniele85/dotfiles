#! /usr/bin/env zsh

setopt errreturn pipefail

usage() {
  echo "Usage: $0 [--dry-run] [-d|--dest DEST_ROOT] <source_album_dir>..." >&2
  exit 1
}

sanitize_component() {
  local value="$1"
  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  value="${value//\//-}"
  value="${value//:/ -}"
  value="${value//\"/}"
  value="${value//\*/-}"
  value="${value//\?/}"
  value="${value//</(}"
  value="${value//>/)}"
  value="${value//|/-}"
  value="$(printf '%s' "$value" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//')"
  printf '%s\n' "$value"
}

read_album_metadata() {
  local mp3_file="$1"
  python3 - "$mp3_file" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

path = Path(sys.argv[1])
cmd = [
    "ffprobe",
    "-v", "error",
    "-show_entries", "format_tags",
    "-of", "json",
    str(path),
]
proc = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    stdin=subprocess.DEVNULL,
)
if proc.returncode != 0:
    raise SystemExit(proc.returncode)

data = json.loads(proc.stdout or "{}")
tags = {k.lower(): v for k, v in data.get("format", {}).get("tags", {}).items()}

artist = tags.get("album_artist") or tags.get("albumartist") or tags.get("artist") or ""
album = tags.get("album") or ""

def first_year_from(*keys):
    for key in keys:
        year_raw = tags.get(key)
        if not year_raw:
            continue
        year = ""
        for ch in year_raw:
            if ch.isdigit():
                year += ch
                if len(year) == 4:
                    return year
            elif year:
                break
    return ""

year = ""
year = first_year_from(
    "originaldate",
    "original_date",
    "originalyear",
    "original_year",
    "original release date",
    "original release year",
    "originalreleasedate",
    "originalreleaseyear",
    "date",
    "year",
)

print(artist)
print(album)
print(year)
PY
}

move_album() {
  local source_dir="$1"
  local dest_root="$2"
  local hostname="$3"
  local target_dir="$4"
  local dry_run="$5"
  local remote_host remote_path remote_parent quoted_remote_parent quoted_remote_path

  if (( dry_run )); then
    echo "Would move ${source_dir} -> ${target_dir}" >&2
    return
  fi

  if [[ "$hostname" == "daniele-HP" ]]; then
    mkdir -p "${target_dir:h}"
    mv "$source_dir" "$target_dir"
    touch "$target_dir"
    return
  fi

  remote_host="${dest_root%%:*}"
  remote_path="${target_dir#${remote_host}:}"
  remote_parent="${remote_path:h}"
  quoted_remote_parent="$(printf '%q' "$remote_parent")"
  quoted_remote_path="$(printf '%q' "$remote_path")"

  ssh -n "$remote_host" "mkdir -p -- $quoted_remote_parent"
  rsync -asP --remove-source-files "$source_dir"/ "$target_dir"/
  ssh -n "$remote_host" "touch -- $quoted_remote_path"
  find "$source_dir" -depth -type d -empty -delete
  [[ ! -e "$source_dir" ]] || rmdir "$source_dir" 2>/dev/null || true
}

move_one_album() {
  local dry_run="$1"
  local source_dir="$2"
  local dest_root="$3"
  local first_mp3 hostname artist album year safe_artist safe_album target_dir
  local target_root target_prefix quoted_target_dir
  local -a metadata

  [[ -n "$source_dir" ]] || usage
  [[ -d "$source_dir" ]] || { echo "Source directory not found: $source_dir" >&2; return 1; }

  first_mp3="$(find "$source_dir" -type f -iname '*.mp3' | LC_ALL=C sort | head -n 1)"
  [[ -n "$first_mp3" ]] || { echo "No mp3 found in: $source_dir" >&2; return 1; }

  metadata=("${(@f)$(read_album_metadata "$first_mp3")}")
  (( ${#metadata[@]} >= 3 )) || { echo "Unable to read metadata from: $first_mp3" >&2; return 1; }

  artist="${metadata[1]}"
  album="${metadata[2]}"
  year="${metadata[3]}"

  [[ -n "$artist" ]] || { echo "Missing album artist/artist tag in: $first_mp3" >&2; return 1; }
  [[ -n "$album" ]] || { echo "Missing album tag in: $first_mp3" >&2; return 1; }
  [[ -n "$year" ]] || { echo "Missing year/date tag in: $first_mp3" >&2; return 1; }

  safe_artist="$(sanitize_component "$artist")"
  safe_album="$(sanitize_component "$album")"
  [[ -n "$safe_artist" && -n "$safe_album" ]] || { echo "Sanitized path component is empty" >&2; return 1; }

  hostname="$(hostname -s 2>/dev/null || hostname)"
  source_dir="${source_dir:A}"

  if [[ "$hostname" == "daniele-HP" ]]; then
    if [[ "$dest_root" == *:* ]]; then
      target_root="${dest_root#*:}"
    else
      target_root="$dest_root"
    fi
    [[ -d "$target_root" ]] || { echo "Destination root not found: $target_root" >&2; return 1; }
    target_dir="${target_root:A}/${safe_artist}/${year} - ${safe_album}"
    [[ ! -e "$target_dir" ]] || { echo "Target already exists: $target_dir" >&2; return 1; }
  else
    [[ "$dest_root" == *:* ]] || { echo "Remote destination must be in host:path form: $dest_root" >&2; return 1; }
    target_prefix="${dest_root%%:*}"
    target_root="${dest_root#*:}"
    target_dir="${target_prefix}:${target_root}/${safe_artist}/${year} - ${safe_album}"
    quoted_target_dir="$(printf '%q' "${target_dir#${target_prefix}:}")"
    if ssh -n "$target_prefix" "test ! -e $quoted_target_dir"; then
      :
    else
      echo "Target already exists: $target_dir" >&2
      return 1
    fi
  fi

  move_album "$source_dir" "$dest_root" "$hostname" "$target_dir" "$dry_run"
  if (( ! dry_run )); then
    echo "$target_dir"
  fi
}

main() {
  local dry_run=0
  local dest_root="hp:/media/Esterno/Musica futura/Autoimport"
  local source_dir
  local -a source_dirs
  source_dirs=()

  while (( $# > 0 )); do
    case "$1" in
      --dry-run)
        dry_run=1
        shift
        ;;
      -d|--dest)
        shift
        [[ $# -gt 0 ]] || { echo "Missing destination after -d/--dest" >&2; usage; }
        dest_root="$1"
        shift
        ;;
      --dest=*)
        dest_root="${1#*=}"
        [[ -n "$dest_root" ]] || { echo "Missing destination after --dest=" >&2; usage; }
        shift
        ;;
      -h|--help)
        usage
        ;;
      --)
        shift
        source_dirs+=("$@")
        break
        ;;
      --*)
        echo "Unknown option: $1" >&2
        usage
        ;;
      *)
        source_dirs+=("$1")
        shift
        ;;
    esac
  done

  (( ${#source_dirs[@]} > 0 )) || usage

  for source_dir in "${source_dirs[@]}"; do
    move_one_album "$dry_run" "$source_dir" "$dest_root"
  done
}

main "$@"
