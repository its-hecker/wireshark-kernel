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
kernel_ref="${KERNEL_REF:-cnb-boot-diagnostic}"
git clone --depth=1 --branch "$kernel_ref" --recurse-submodules https://github.com/its-hecker/wireshark-kernel.git private/msm-google
kernel_sha=$(git -C private/msm-google rev-parse HEAD)
[ "$kernel_sha" = 72c95de548e83e9113080d6827b822d0302e9d8d ] || { echo "Diagnostic source revision changed; review it before building" >&2; exit 1; }
grep -Fxq '# CONFIG_THINLTO is not set' private/msm-google/arch/arm64/configs/floral_defconfig || { echo "Diagnostic source must use Full LTO" >&2; exit 1; }
grep -Fxq 'CONFIG_CFI_CLANG=y' private/msm-google/arch/arm64/configs/floral_defconfig || { echo "Diagnostic source must retain CFI" >&2; exit 1; }
# Match the compiler and Full LTO profile extracted from the restored ROM kernel.
# This is a diagnostic build profile, not a confirmed phone boot fix.
clang_commit=9b144befdfd93b90e02c663504fb9f4b95f9faf8
clang_checkout="$workspace/toolchains/aosp-clang"
clang_path=toolchains/aosp-clang/clang-r596125
if [ ! -d "$clang_checkout/.git" ]; then
  mkdir -p "$clang_checkout"
  git init "$clang_checkout"
  git -C "$clang_checkout" remote add origin https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86
fi
git -C "$clang_checkout" fetch --filter=blob:none --depth=1 origin "$clang_commit"
git -C "$clang_checkout" sparse-checkout init --cone
git -C "$clang_checkout" sparse-checkout set clang-r596125
git -C "$clang_checkout" checkout --detach "$clang_commit"
[ "$(git -C "$clang_checkout" rev-parse HEAD)" = "$clang_commit" ]
LD_LIBRARY_PATH="$workspace/$clang_path/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
  "$workspace/$clang_path/bin/clang" --version > "$project/dist/clang-version.txt"
for marker in 'Android (15071444,' 'based on r596125' 'clang version 22.0.2' 'de03d430485c884861198b25459851f429cbdbad'; do
  grep -Fq "$marker" "$project/dist/clang-version.txt" || {
    echo "Diagnostic toolchain does not match the restored kernel: $marker" >&2
    exit 1
  }
done
printf 'Repository: %s\nCommit: %s\nDirectory: %s\nLTO: full\nStatus: diagnostic, no phone boot verification\n' \
  'https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86' \
  "$clang_commit" "$clang_path" > "$project/dist/toolchain-provenance.txt"
cat "$project/dist/clang-version.txt"
printf '%s\n' "$kernel_ref" > "$project/dist/kernel-ref.txt"
if [ -f private/msm-google/tests/suspend_wakeup_host.py ]; then
  python3 private/msm-google/tests/suspend_wakeup_host.py
fi
if [ -f private/msm-google/tests/module_loader_host.py ]; then
  python3 private/msm-google/tests/module_loader_host.py
fi
repo manifest -r -o "$project/dist/workspace-manifest.xml"
git -C private/msm-google submodule status --recursive > "$project/dist/kernel-submodules.txt"
printf '%s\n' "$kernel_sha" > "$project/dist/kernel-commit.txt"
# Use the selected branch's CFI-enabled floral_defconfig. Normalization by
# olddefconfig is allowed; all resolved settings are saved with the artifact.
cat > private/msm-google/build.config.wireshark <<'CONFIG'
KERNEL_DIR=private/msm-google
. ${ROOT_DIR}/${KERNEL_DIR}/build.config.floral.common.clang
CLANG_PREBUILT_BIN=toolchains/aosp-clang/clang-r596125/bin
LD_LIBRARY_PATH=${ROOT_DIR}/toolchains/aosp-clang/clang-r596125/lib:${LD_LIBRARY_PATH}
export LD_LIBRARY_PATH
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
for marker in '# CONFIG_THINLTO is not set' 'CONFIG_LTO_CLANG=y' 'CONFIG_CFI_CLANG=y' '# CONFIG_CFI_PERMISSIVE is not set' 'CONFIG_SHADOW_CALL_STACK=y' 'CONFIG_MODVERSIONS=y'; do
  grep -Fxq "$marker" "$DIST_DIR/.config" || {
    echo "Resolved diagnostic config is missing: $marker" >&2
    exit 1
  }
done
bash "$project/scripts/package.sh" "$DIST_DIR" "$kernel_sha"


