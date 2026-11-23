#!/usr/bin/env sh
# One-line installer for Ultimate Orchestration Skills (POSIX sh, no Node.js required).
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client codex
#   curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client claude
#   curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client antigravity

set -eu

REPO_URL="https://github.com/ahmedkececi/ultimate-orchestration-skills.git"
REF="main"
CLIENT=""
PRESET=""
TARGET_DIR=""
SOURCE_DIR=""
WITH_PROVIDER=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Ultimate Orchestration Skills — one-line installer

Usage:
  install.sh [options]

Options:
  --client <name>     Target client: codex (default), claude, or antigravity
  --preset <name>     Install a single coordinator preset:
                        sol | astra | opus | fable | neon
  --with-provider     Also install add-provider-orchestration-skills
  --dir <path>        Override destination skills directory
  --ref <branch|tag>  Git branch or tag to install (default: main)
  --source <path>     Copy from a local clone instead of cloning from GitHub
  --dry-run           Print what would be installed (and which existing skill
                      folders would be backed up) without writing files
  -h, --help          Show this help message

Examples:
  curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client codex
  curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client claude --with-provider
  curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --client antigravity
  curl -fsSL https://raw.githubusercontent.com/ahmedkececi/ultimate-orchestration-skills/main/install.sh | sh -s -- --preset sol

Existing skill folders are never deleted: each one is moved to
<parent of the skills dir>/skill-backups/<skill>-<UTC timestamp>/ (outside the
skills dir, so clients do not load it as a duplicate skill) before the upstream
copy is installed, and files that are not part of upstream are listed.
EOF
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --client)
      [ "$#" -ge 2 ] || fail "--client requires a value"
      CLIENT="$2"
      shift 2
      ;;
    --preset)
      [ "$#" -ge 2 ] || fail "--preset requires a value"
      PRESET="$2"
      shift 2
      ;;
    --with-provider)
      WITH_PROVIDER=1
      shift
      ;;
    --dir)
      [ "$#" -ge 2 ] || fail "--dir requires a value"
      TARGET_DIR="$2"
      shift 2
      ;;
    --ref)
      [ "$#" -ge 2 ] || fail "--ref requires a value"
      REF="$2"
      shift 2
      ;;
    --source)
      [ "$#" -ge 2 ] || fail "--source requires a value"
      SOURCE_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1 (use --help)"
      ;;
  esac
done

case "$REF" in
  ""|*..*|*[!A-Za-z0-9._/-]*)
    fail "invalid --ref value: $REF"
    ;;
esac

SKILLS=""
STARTER_CMD=""

if [ -n "$PRESET" ]; then
  case "$PRESET" in
    sol|sol-orchestration)
      SKILLS="sol-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".agents/skills"
      STARTER_CMD="\$sol-orchestration"
      ;;
    astra|astra-orchestration)
      SKILLS="astra-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".agents/skills"
      STARTER_CMD="\$astra-orchestration"
      ;;
    neon|neon-orchestration)
      SKILLS="neon-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".agents/skills"
      STARTER_CMD="/neon-orchestration"
      ;;
    opus|opus-orchestration)
      SKILLS="opus-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".claude/skills"
      STARTER_CMD="/opus-orchestration"
      ;;
    fable|fable-orchestration)
      SKILLS="fable-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".claude/skills"
      STARTER_CMD="/fable-orchestration"
      ;;
    *)
      fail "unsupported --preset: $PRESET (expected: sol, astra, opus, fable, or neon)"
      ;;
  esac
else
  [ -n "$CLIENT" ] || CLIENT="codex"
  case "$CLIENT" in
    codex)
      SKILLS="sol-orchestration astra-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".agents/skills"
      STARTER_CMD="\$sol-orchestration"
      ;;
    claude|claude-code)
      SKILLS="opus-orchestration fable-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".claude/skills"
      STARTER_CMD="/opus-orchestration"
      ;;
    antigravity|agy)
      SKILLS="neon-orchestration update-orchestration-skills"
      [ -n "$TARGET_DIR" ] || TARGET_DIR=".agents/skills"
      STARTER_CMD="/neon-orchestration"
      ;;
    *)
      fail "unsupported --client: $CLIENT (expected: codex, claude, or antigravity)"
      ;;
  esac
fi

if [ "$WITH_PROVIDER" -eq 1 ]; then
  SKILLS="$SKILLS add-provider-orchestration-skills"
fi

# Trim trailing slashes so dirname behaves the same for "dir" and "dir/".
TARGET_DIR_TRIMMED=$TARGET_DIR
while :; do
  case "$TARGET_DIR_TRIMMED" in
    ?*/) TARGET_DIR_TRIMMED=${TARGET_DIR_TRIMMED%/} ;;
    *) break ;;
  esac
done
BACKUP_ROOT="$(dirname -- "$TARGET_DIR_TRIMMED")/skill-backups"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)

# Print files that exist in the old folder ($1) but not in the upstream copy ($2).
warn_project_local() {
  old="$1"
  new="$2"
  [ -d "$new" ] || return 0
  find "$old" \( -type f -o -type l \) -print | while IFS= read -r path; do
    rel=${path#"$old"/}
    if [ ! -e "$new/$rel" ] && [ ! -L "$new/$rel" ]; then
      printf '  warning: project-local file not in upstream: %s\n' "$rel"
    fi
  done
}

# Pick a backup folder name that does not exist yet.
backup_path_for() {
  base="$BACKUP_ROOT/$1-$STAMP"
  candidate="$base"
  n=1
  while [ -e "$candidate" ] || [ -L "$candidate" ]; do
    n=$((n + 1))
    candidate="$base-$n"
  done
  printf '%s\n' "$candidate"
}

if [ "$DRY_RUN" -eq 1 ]; then
  printf 'Dry run — no files written.\n'
  printf 'Destination: %s\n' "$TARGET_DIR"
  printf 'Ref: %s\n' "$REF"
  printf 'Skills:\n'
  for skill in $SKILLS; do
    printf '  - %s\n' "$skill"
  done
  for skill in $SKILLS; do
    dst="$TARGET_DIR/$skill"
    if [ -e "$dst" ] || [ -L "$dst" ]; then
      printf 'Would back up %s -> %s\n' "$dst" "$(backup_path_for "$skill")"
      if [ -n "$SOURCE_DIR" ]; then
        warn_project_local "$dst" "$SOURCE_DIR/skills/$skill"
      else
        printf '  (project-local file check needs the upstream copy; it runs during a real install)\n'
      fi
    fi
  done
  exit 0
fi

TMP_DIR=""
cleanup() {
  if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
    rm -rf -- "$TMP_DIR"
  fi
}
trap cleanup 0 INT TERM

if [ -n "$SOURCE_DIR" ]; then
  REPO_ROOT="$SOURCE_DIR"
else
  command -v git >/dev/null 2>&1 || fail "git is required to install from GitHub"
  TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ultimate-orchestration-skills.XXXXXXXX")
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$TMP_DIR/repo" >/dev/null 2>&1 \
    || fail "failed to clone $REPO_URL (ref: $REF)"
  REPO_ROOT="$TMP_DIR/repo"
fi

[ -d "$REPO_ROOT/skills" ] || fail "skills directory not found under $REPO_ROOT"

mkdir -p -- "$TARGET_DIR"

for skill in $SKILLS; do
  src="$REPO_ROOT/skills/$skill"
  dst="$TARGET_DIR/$skill"
  [ -d "$src" ] || fail "missing skill directory: $src"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    backup=$(backup_path_for "$skill")
    mkdir -p -- "$BACKUP_ROOT"
    mv -- "$dst" "$backup"
    printf 'Backed up %s -> %s\n' "$dst" "$backup"
    warn_project_local "$backup" "$src"
  fi
  cp -R -- "$src" "$dst"
  printf 'Installed %s -> %s\n' "$skill" "$dst"
done

printf '\nDone! Open your client in this project root and paste:\n'
printf '  %s Check my installed CLIs (claude, codex, agy) and sign-in status, guide me through installing or signing in to the ones I want to use, set up .orchestration/ if missing, and wait for me to give you a task to delegate.\n' "$STARTER_CMD"
