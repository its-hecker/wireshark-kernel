#!/sbin/sh
properties() { '
kernel.string=WireShark for Pixel 4 XL
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=1
device.name1=coral
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }

BLOCK=boot
IS_SLOT_DEVICE=1
SLOT_SELECT=active
RAMDISK_COMPRESSION=auto
PATCH_VBMETA_FLAG=0
. tools/ak3-core.sh

# Core initialization resolves BLOCK and SLOT but does not write partitions.
[ -s Image.lz4 ] && [ -s dtb ] && [ -s dtbo.img ] || abort "Missing kernel or device-tree payload."
[ -s modules.sha256 ] || abort "Missing module compatibility manifest."
[ -s module-symbols.txt ] && [ -x tools/module-check ] || abort "Missing module ABI checker."
while read -r expected name; do
  [ -n "$expected" ] && [ -n "$name" ] || abort "Invalid module manifest."
  case "$name" in *[!A-Za-z0-9_.-]*) abort "Invalid module name.";; esac
  matched=0
  found=0
  readable=0
  failure=""
  reference="module-reference/$name"
  [ -s "$reference" ] || abort "Missing module reference: $name"
  for root in /vendor/lib/modules /system/vendor/lib/modules /vendor_dlkm/lib/modules /system/lib/modules; do
    for candidate in $(find -L "$root" -type f -name "$name" 2>/dev/null); do
      found=1
      [ -r "$candidate" ] || continue
      readable=1
      if failure=$(tools/module-check "$candidate" "$reference" module-symbols.txt 2>&1); then
        matched=1
        break
      fi
    done
    [ "$matched" = 1 ] && break
  done
  [ "$found" = 1 ] || abort "ROM module $name is unavailable. Mount Vendor in recovery, then retry."
  [ "$readable" = 1 ] || abort "Cannot read ROM module $name. Check the Vendor mount."
  if [ "$matched" != 1 ]; then
    ui_print "$failure"
    abort "ROM module $name failed ABI validation. No partitions were changed."
  fi
done < modules.sha256
ui_print "ROM module ABI checks passed."

case "$SLOT" in _a|_b) ;; *) abort "Invalid active slot.";; esac
dtbo_block=/dev/block/by-name/dtbo$SLOT
[ -b "$dtbo_block" ] || dtbo_block=/dev/block/bootdevice/by-name/dtbo$SLOT
[ -b "$BLOCK" ] && [ -b "$dtbo_block" ] || abort "Boot or DTBO partition unavailable."
[ "$(wc -c < dtbo.img)" -le "$(blockdev --getsize64 "$dtbo_block")" ] || abort "DTBO exceeds partition size."
backup=/sdcard/WireShark-backups/$(date +%Y%m%d-%H%M%S)-$$$SLOT
mkdir -p "$backup" || abort "Cannot create partition backup."
dd if="$BLOCK" of="$backup/boot$SLOT.img" bs=4096 || abort "Boot backup failed."
dd if="$dtbo_block" of="$backup/dtbo$SLOT.img" bs=4096 || abort "DTBO backup failed."
sync
ui_print "Partition backups: $backup"
split_boot
flash_boot
flash_generic dtbo

