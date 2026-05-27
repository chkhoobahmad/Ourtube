#!/bin/bash

source /tmp/env_vars.txt
BACKUP_DIR=$(cat /tmp/backup_dir_path.txt)
CHANNEL_NAME=${CHANNEL_NAME}
REPO_OWNER=${REPO_OWNER}
REPO_NAME=${REPO_NAME}
BRANCH=${BRANCH}

BACKUP_FILE_COUNT=$(find "$BACKUP_DIR" -type f 2>/dev/null | wc -l)
if [ "$BACKUP_FILE_COUNT" -eq 0 ]; then
  echo "WARNING: No files in backup directory — all downloads may have failed."
  git fetch origin "$BRANCH"
  git reset --hard origin/"$BRANCH"
  mkdir -p videos
  if [ ! -f "videos/README.md" ]; then
    {
      echo "# 📺 DOWNLOADED CHANNELS"
      echo ""
      echo "----"
      echo ""
      echo "> No channels downloaded yet."
    } > videos/README.md
    git add -f videos/README.md
    if ! git diff --cached --quiet; then
      git commit -m "[AVASAM] Initialize videos folder [skip ci]"
      git push origin HEAD:"$BRANCH" || true
    fi
  fi
  echo "No video files to push. Exiting."
  exit 0
fi

urlencode() {
  python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

regenerate_master_readme() {
  MASTER_README="videos/README.md"
  {
    echo "# 📺 DOWNLOADED CHANNELS"
    echo ""
    echo "----"
    echo ""
  } > "$MASTER_README"
  NUM=0
  for channel in videos/*/; do
    [ -d "$channel" ] || continue
    CHANNEL_FOLDER=$(basename "$channel")
    NUM=$((NUM + 1))
    CHANNEL_ENCODED=$(urlencode "$CHANNEL_FOLDER")
    CHANNEL_LINK="https://github.com/${REPO_OWNER}/${REPO_NAME}/tree/${BRANCH}/videos/${CHANNEL_ENCODED}"
    VIDEO_COUNT=$(find "$channel" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    printf -- "- **%s** - 🎬 [%s](%s) - **%d videos**\n" "$NUM" "$CHANNEL_FOLDER" "$CHANNEL_LINK" "$VIDEO_COUNT" >> "$MASTER_README"
  done
  if [ $NUM -eq 0 ]; then
    echo "> No channels downloaded yet." >> "$MASTER_README"
  fi
}

git fetch origin "$BRANCH"
git reset --hard origin/"$BRANCH"
mkdir -p videos
cp -r "$BACKUP_DIR"/* videos/

git add -f videos/
regenerate_master_readme
git add -f videos/README.md

if ! git diff --cached --quiet; then
  git commit -m "[AVASAM] YouTube channel download: $CHANNEL_NAME [skip ci]"
  PUSH_RETRY=0
  while [ $PUSH_RETRY -lt 10 ]; do
    PUSH_RETRY=$((PUSH_RETRY + 1))
    if timeout 300 git push origin HEAD:"$BRANCH"; then
      echo "Push successful!"
      break
    else
      echo "Push failed, retry $PUSH_RETRY/10..."
      sleep 5
      git fetch origin "$BRANCH"
      git reset --hard origin/"$BRANCH"
      cp -r "$BACKUP_DIR"/* videos/
      git add -f videos/
      regenerate_master_readme
      git add -f videos/README.md
      git diff --cached --quiet || git commit -m "[AVASAM] YouTube channel download: $CHANNEL_NAME [skip ci]"
    fi
  done
fi

echo "=========================================="
echo "All files pushed successfully!"
echo "Channel: $CHANNEL_NAME"
echo "made in AVASAM (https://avasam.ir)"
echo "=========================================="
