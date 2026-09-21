#!/bin/sh
# Jibri finalize hook: restructure the recording to the layout the backend's
# finalize worker expects — a flat <room_name>.mp4 directly in the
# recordings dir. Jibri hands us the session directory ($1) containing
# <room>_<timestamp>.mp4 and metadata.json; we move the MP4 out under its
# bare room name and drop the session dir.
DIR="$1"
f=$(ls "$DIR"/*.mp4 2>/dev/null | head -1)
[ -z "$f" ] && exit 0
base=$(basename "$f" .mp4)
room=$(printf '%s' "$base" | cut -d_ -f1)
case "$room" in
  si-????????)
    mv -f "$f" "/config/recordings/$room.mp4" && rm -rf "$DIR"
    ;;
esac
exit 0
