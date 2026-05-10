#!/usr/bin/env bash

# This script links all skill folders in the current directory to ~/.agents/skills
# so that they are automatically available to your local agents.

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.agents/skills"

if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: Target directory $TARGET_DIR does not exist."
  exit 1
fi

echo "Linking skills from $SOURCE_DIR to $TARGET_DIR..."

# Find all directories that contain a SKILL.md file
for skill_path in "$SOURCE_DIR"/*/SKILL.md; do
  # Check if glob matched anything
  [ -e "$skill_path" ] || continue
  
  # Get the directory name (the skill name)
  skill_dir=$(dirname "$skill_path")
  skill_name=$(basename "$skill_dir")
  
  target_link="$TARGET_DIR/$skill_name"
  
  if [ -L "$target_link" ]; then
    echo "  [SKIP] $skill_name is already linked."
  elif [ -d "$target_link" ]; then
    echo "  [WARN] $skill_name exists in target but is not a symlink. Skipping."
  else
    ln -s "$skill_dir" "$target_link"
    echo "  [LINKED] $skill_name"
  fi
done

echo "Done! All local skills are now available to your agents."
