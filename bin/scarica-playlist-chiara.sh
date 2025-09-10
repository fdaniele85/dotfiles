#!/usr/bin/env zsh
set -euo pipefail

ALBUM_NAME="Playlist Chiara"

if [[ $# -ne 1 ]]; then
#  URL="https://www.youtube.com/playlist?list=PL1SHutkY63dMZ8bT597BhpAd8Y4na5D4m"
  URL="https://open.spotify.com/playlist/54qLAaSm8BEyikgPlwdqVD"
else
  URL="$1"
fi

# for cmd in yt-dlp ffmpeg; do
#   command -v "$cmd" >/dev/null 2>&1 || { echo "Errore: manca '$cmd' nel PATH."; exit 2; }
# done

# /home/daniele/.venvs/scripts_1553aca88f67/bin/yt-dlp \
#   -x --audio-format mp3 --audio-quality 0 \
#   --embed-metadata \
#   --embed-thumbnail --convert-thumbnails jpg \
#   --metadata-from-title "%(artist)s - %(title)s" \
#   --parse-metadata "playlist_index:%(track_number)s" \
#   --postprocessor-args "ffmpeg:-metadata album=${ALBUM_NAME}" \
#   -o "%(playlist_index)02d - %(title)s.%(ext)s" \
#   "$URL"

/home/daniele/.venvs/scripts_1553aca88f67/bin/spotdl --dont-filter-results --output "{title}.{output-ext}" --bitrate 320k $URL

album="Playlist Chiara"
artist="Various Artists"

cover="${1:-cover.jpg}"   # puoi passare il nome della cover come 1° argomento

# Se non c'è la cover indicata, prova qualche fallback comune
if [[ ! -f "$cover" ]]; then
  for alt in cover.png Cover.jpg Cover.png folder.jpg folder.png; do
    [[ -f "$alt" ]] && cover="$alt" && break
  done
fi

if [[ ! -f "$cover" ]]; then
  echo "⚠️  Nessuna copertina trovata (es. cover.jpg). Procedo senza cover."
fi


i=1
for file in *.mp3; do
  [[ -f "$file" ]] || continue
  echo "▶ Tagging: $file → track $i"
  eyeD3 --to-v2.3 --no-color --quiet \
        --remove-frames=TPOS \
        --remove-images \
        --title "$title" \
        --artist "$artist" \
        --album "$album" \
        --album-artist "$artist" \
        --track "$i" \
        "$file"

  ((i++))
done

if [[ -f "$cover" ]]; then
  eyeD3 --no-color --quiet \
        --add-image "${cover}:FRONT_COVER" \
        *.mp3
fi

