#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
workspace="$project/workspace"
mkdir -p "$workspace" "$project/dist"
cd "$workspace"
git config --global user.name 'WireShark Builder'
git config --global user.email 'builder@users.noreply.github.com'
repo init -u https://android.googlesource.com/kernel/manifest -b android-msm-coral-4.14-android13 --depth=1
repo sync -c -j4 --no-tags --fail-fast
rm -rf private/msm-google
git clone --depth=1 --branch cnb --recurse-submodules https://github.com/its-hecker/infinity_cnb_kernel_google_msm-4.14.git private/msm-google
kernel_sha=$(git -C private/msm-google rev-parse HEAD)
repo manifest -r -o "$project/dist/workspace-manifest.xml"
git -C private/msm-google submodule status --recursive > "$project/dist/kernel-submodules.txt"
printf '%s\n' "$kernel_sha" > "$project/dist/kernel-commit.txt"
# Use the ROM's unchanged CFI-enabled floral_defconfig. Normalization by
# olddefconfig is allowed; all resolved settings are saved with the artifact.
cat > private/msm-google/build.config.wireshark <<'CONFIG'
KERNEL_DIR=private/msm-google
. ${ROOT_DIR}/${KERNEL_DIR}/build.config.floral.common.clang
POST_DEFCONFIG_CMDS=""
CONFIG
export BUILD_CONFIG=private/msm-google/build.config.wireshark
export OUT_DIR="$workspace/out"
export DIST_DIR="$workspace/out/dist"
export KBUILD_BUILD_USER=wireshark
export KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP="$(git -C private/msm-google show -s --format=%cD HEAD)"
export SOURCE_DATE_EPOCH="$(git -C private/msm-google show -s --format=%ct HEAD)"
bash build/build.sh -j"$(nproc)" 2>&1 | tee "$project/dist/build.log"
bash "$project/scripts/package.sh" "$DIST_DIR" "$kernel_sha"
