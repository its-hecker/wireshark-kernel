#!/usr/bin/env bash
set -euo pipefail
# Import the complete source tree, without rewriting either existing branch.
# The new commits are parented to this repository's main commit; original
# source URLs and exact revisions are recorded in their commit messages.
git config user.name 'WireShark Source Import'
git config user.email 'builder@users.noreply.github.com'
source_url=https://github.com/its-hecker/infinity_cnb_kernel_google_msm-4.14.git
while read -r branch expected; do
  remote_ref=$(git ls-remote --heads origin "refs/heads/$branch")
  if [ -n "$remote_ref" ]; then
    echo "Source branch $branch already exists; preserving it."
    continue
  fi
  git fetch --depth=1 --no-tags "$source_url" "$expected"
  actual=$(git rev-parse FETCH_HEAD)
  [ "$actual" = "$expected" ] || { echo "Source revision mismatch"; exit 1; }
  tree=$(git rev-parse 'FETCH_HEAD^{tree}')
  imported=$(printf 'Import %s kernel source tree\n\nSource: %s\nSource-commit: %s\nSource-tree: %s\n\nOptimization credits and regression tests are retained in the source tree.\n' "$branch" "$source_url" "$actual" "$tree" | git commit-tree "$tree" -p HEAD)
  # Empty expected ref is a creation-only lease, never a branch overwrite.
  git push --force-with-lease="refs/heads/$branch:" origin "$imported:refs/heads/$branch"
done <<'SOURCES'
cnb e8d36b72ab353f841892cd64b7ad20491f5479d5
cnb-optimized a42fa7f5ca4caefb22ae28cf639a00f16fb7dcae
SOURCES
