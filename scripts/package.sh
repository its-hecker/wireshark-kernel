#!/usr/bin/env bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
output=$(realpath "$1")
kernel_sha="$2"
installer_sha=020dfeccf9d7e962a48400fc94d3e451df92eeade8
stage="$project/packaging"
mkdir -p "$project/dist"
rm -rf "$stage"
git clone https://github.com/osm0sis/AnyKernel3.git "$stage"
git -C "$stage" checkout --detach "$installer_sha"
rm -rf "$stage/.git" "$stage/.github" "$stage/ramdisk" "$stage/patch" "$stage/modules"
rm -f "$stage/README.md" "$stage/.gitignore"
cp "$project/anykernel.sh" "$stage/anykernel.sh"
cp "$output/Image.lz4" "$stage/Image.lz4"
cp "$output/dtbo.img" "$stage/dtbo.img"
cat "$output/sm8150.dtb" "$output/sm8150-v2.dtb" > "$stage/dtb"
cp "$output/.config" "$project/dist/kernel.config"
rm -rf "$project/module-staging"
mkdir -p "$project/module-staging"
test -s "$output/modules.tar.gz"
tar -xzf "$output/modules.tar.gz" -C "$project/module-staging"
python3 "$project/scripts/module_manifest.py" "$project/module-staging" "$stage/modules.sha256"
cp "$output/modules.tar.gz" "$project/dist/matching-modules.tar.gz"
printf 'Kernel: %s\nAnyKernel3: %s\nDevice: coral\n' "$kernel_sha" "$installer_sha" > "$stage/version"
cp "$stage/version" "$project/dist/provenance.txt"
chmod 755 "$stage/anykernel.sh" "$stage/META-INF/com/google/android/update-binary" "$stage/tools/"*
zipfile="$project/dist/WireShark-coral-${kernel_sha:0:12}.zip"
rm -f "$zipfile"
(cd "$stage" && zip -9 -r "$zipfile" .)
python3 "$project/scripts/validate_zip.py" "$zipfile"
(cd "$project/dist" && sha256sum "$(basename "$zipfile")" > "$(basename "$zipfile").sha256")
