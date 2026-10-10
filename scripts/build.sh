#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
workspace="$project/workspace"
mkdir -p "$workspace" "$project/dist"
exec > >(tee "$project/dist/build.log") 2>&1
# Keep linker resource usage visible even while LTO has no compiler output.
(while sleep 30; do date -u; free -m; done) &
resource_monitor_pid=$!
trap 'kill "$resource_monitor_pid" 2>/dev/null || true' EXIT
cd "$workspace"
git config --global user.name 'WireShark Builder'
git config --global user.email 'builder@users.noreply.github.com'
repo init -u https://android.googlesource.com/kernel/manifest -b android-msm-coral-4.14-android13 --depth=1
repo sync -c -j4 --no-tags --fail-fast
rm -rf private/msm-google
kernel_ref="${KERNEL_REF:-cnb-optimized}"
git clone --depth=1 --branch "$kernel_ref" --recurse-submodules https://github.com/its-hecker/wireshark-kernel.git private/msm-google
kernel_sha=$(git -C private/msm-google rev-parse HEAD)
printf '%s\n' "$kernel_ref" > "$project/dist/kernel-ref.txt"
if [ -f private/msm-google/tests/suspend_wakeup_host.py ]; then
  python3 private/msm-google/tests/suspend_wakeup_host.py
fi
repo manifest -r -o "$project/dist/workspace-manifest.xml"
git -C private/msm-google submodule status --recursive > "$project/dist/kernel-submodules.txt"
printf '%s\n' "$kernel_sha" > "$project/dist/kernel-commit.txt"
# Use the selected branch's CFI-enabled floral_defconfig. Normalization by
# olddefconfig is allowed; all resolved settings are saved with the artifact.
cat > private/msm-google/build.config.wireshark <<'CONFIG'
KERNEL_DIR=private/msm-google
. ${ROOT_DIR}/${KERNEL_DIR}/build.config.floral.common.clang
FILES="${FILES} Module.symvers"
POST_DEFCONFIG_CMDS=""
# Wi-Fi and touch drivers are already built from this source tree.
EXT_MODULES=""
# This tree's modules_install does not populate AOSP's private debug directory.
UNSTRIPPED_MODULES=""
# AnyKernel3 preserves the installed ramdisk; only export the built .ko files.
BUILD_INITRAMFS=""
CONFIG
export BUILD_CONFIG=private/msm-google/build.config.wireshark
# This checkout and OUT_DIR are new on each hosted runner. mrproper has no
# config and trips KernelSU-Next's manual-hook check before defconfig runs.
export SKIP_MRPROPER=1
# The flashable package does not use kernel header archives.
export SKIP_CP_KERNEL_HDR=1
export OUT_DIR="$workspace/out"
export DIST_DIR="$workspace/out/dist"
export KBUILD_BUILD_USER=wireshark
export KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP="$(git -C private/msm-google show -s --format=%cD HEAD)"
export SOURCE_DATE_EPOCH="$(git -C private/msm-google show -s --format=%ct HEAD)"
bash build/build.sh -j"$(nproc)"
bash "$project/scripts/package.sh" "$DIST_DIR" "$kernel_sha"

