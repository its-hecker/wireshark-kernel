# Recovering from the reported WireShark boot failure

## Affected artifact and current status

On 2026-10-11, a user reported that their phone stayed at the Google logo
after flashing the newly delivered floral kernel. The expected artifact is
`WireShark-floral-ad869a2e1f74.zip` from
[run 38161422852](https://github.com/its-hecker/wireshark-kernel/actions/runs/38161422852).
Confirm the actual flashed filename in the recovery log before attributing
the report to this exact build. The uploaded archive now provides pre-flash images and an OrangeFox
startup log, but no failed-boot crash log or post-flash image, so the root
cause remains unconfirmed.

Do not flash this artifact again or wipe data to resolve this kernel failure.
The installer changes only boot and DTBO in the selected slot. Restore the
pre-flash images from the same device/ROM.

## Restored-ROM module evidence

The maintainer restored the pre-flash boot backup and Android boots again.
Keep that working kernel installed during this investigation.

The complete `/vendor/lib/modules` archive supplied on 2026-10-11 contains
all 27 modules in the reported failing build's reference set. Every module
passes its static ABI checker: 2,555 imported symbol CRC records, exported
symbols, vermagic feature flags, module-structure size and legacy-CFI mode.
Every module identifies the restored compiler, Clang 22.0.2 build 15071444.
The failed build used Clang 12 and ThinLTO; the working config uses Full LTO.

CFI-mode checks do not compare all function type IDs. Relocation inspection
found differing Wi-Fi IDs for `qdf_vtrace_msg` and `qdf_trace_msg_cmn`.
This establishes a metadata difference, not a failed runtime call or a
confirmed explanation of the bootloop. See the
[full module findings](https://github.com/its-hecker/wireshark-kernel/blob/boot-diagnostic-builder/docs/rom-module-baseline.md).

The separate
[diagnostic profile](https://github.com/its-hecker/wireshark-kernel/blob/boot-diagnostic-builder/docs/diagnostic-profile.md)
uses the exact compiler build and Full LTO while retaining CFI, shadow
call stack and strict CRC checks. The next planned device test uses a
validated temporary boot image with only its kernel replaced. Preserve
its recovery ramdisk and original DTB and leave on-device DTBO untouched.
Do not flash another ZIP or reinstall the failed kernel merely to obtain
a crash log. No diagnostic phone boot has been verified yet.

## Validated temporary diagnostic image

[Diagnostic run 38170155669](https://github.com/its-hecker/wireshark-kernel/actions/runs/38170155669) succeeded using source
`72c95de548e83e9113080d6827b822d0302e9d8d` and builder
`e0e33d10e19ca718cc3d146f4041029179efe693`. The compiler exactly matches
the restored kernel: Clang 22.0.2, r596125, build 15071444, LLVM de03d430.
Full LTO, enforcing CFI, shadow call stack and strict CRC checks remain.
The artifact's configuration matches its embedded config and the supplied
working kernel's configuration, with no resolved-setting differences.

All 27 actual ROM modules pass the fresh ABI checks, including 2,555
imported CRC records. Named CFI type-ID sets and exploratory equality
comparison-ID sets match for all 27 references, including Wi-Fi. This is
a partial metadata comparison, not proof of runtime CFI correctness or
a confirmed explanation of the previous boot failure.

The separately delivered `WireShark-coral-temporary-72c95de548e8.img`
is 67,108,864 bytes, SHA256
`7f06be92b44c65fa0f953f903d1dca8eb7cc08464622e6fdac674bcb591fa1eb`.
It uses the supplied coral backup
`180af97120434546f49b36a63477008c69d34c3cf163caff9ad2fdcde69e4b95`.
Only the kernel payload changes. Its compressed recovery ramdisk, original
DTB and header settings are unchanged. It is specific to this backup and
ROM; do not use it on flame or flash it to a partition.

With the delivered image in the current Windows CMD folder:

```bat
adb reboot bootloader
fastboot getvar product
```

Confirm the product is `coral`, then temporarily load the image:

```bat
fastboot boot WireShark-coral-temporary-72c95de548e8.img
```

This downloads and boots the image in RAM without flashing boot or DTBO.
The backup contains OrangeFox, so this test may start recovery rather than
Android. Report which starts and collect `adb shell cat /proc/version`.
Recovery starting establishes only that the new kernel can start recovery,
not Android compatibility. If Android starts, check Wi-Fi, audio and touch
and send the kernel version before considering another installation.

If it hangs, return to the bootloader with Power + Volume Down and choose
the installed Recovery Mode. The temporary command did not replace the
restored boot image. Collect `adb pull /sys/fs/pstore pstore-temporary-test`
from the working recovery before booting Android normally. Do not repeat a
failed boot just to obtain logs. An empty pstore leaves the failure unresolved.

No diagnostic phone boot has been verified, and the compiled diagnostic
AnyKernel ZIP also replaces DTB/DTBO. It is not the first device test.

## What the uploaded backup establishes

The supplied `logs.zip` contains pre-flash `boot_a.img` and `dtbo_a.img`
from `20261011-203621-1426_a`, an OrangeFox startup log and an empty
pstore directory. It does not contain the image actually written by the
kernel installer or the ZIP installation transcript.

The pre-flash boot image uses header v2 and contains the previously working
Clang 22 `4.14.357-WireShark+` kernel plus a gzip recovery ramdisk.
That ramdisk contains `system/bin/recovery`, `sbin/foxstart.sh`,
OrangeFox resources and recovery init files. OrangeFox was present in the
backed-up boot partition.

Coral uses `BOARD_USES_RECOVERY_AS_BOOT := true`; recovery shares the
boot kernel rather than having an independent recovery kernel/partition.
A replacement kernel that cannot initialize can therefore prevent both
Android and the installed OrangeFox from starting. Recovery being
inaccessible does not by itself establish that its files were erased.

An offline host magiskboot repack of this backup with the new kernel/DTB
preserved the decompressed ramdisk byte for byte (SHA256
`45cf00555aa61d591d53d084fed1d993e7e5ffd8fa90b58e1fddec67cbd80a81`).
This tests repacking with a native host tool; it is not a readback of the
actual flash and does not verify the ARM recovery tool's output on the phone.

The extracted working-kernel configuration differs from this build's
resolved configuration only in `CONFIG_THINLTO` (working: disabled/full
LTO; new build: enabled). Its compiler is Clang 22 rather than Clang 12.
Those are investigation leads, not established causes. The ROM backup's
DTB/DTBO contents and table ordering also differ from the new payloads;
comparison against an earlier unboot-tested ZIP cannot rule out a
device-tree problem.

## Capture the actual failed image before restoring, if still available

If slot a still contains the failed kernel, temporarily boot the known-working
OrangeFox and collect the actual partition image:

```bat
adb shell "dd if=/dev/block/bootdevice/by-name/boot_a of=/sdcard/WireShark-failed-boot_a.img bs=4096"
adb pull /sdcard/WireShark-failed-boot_a.img
```

This is a read of the boot partition into a separate file, not a flash.
If the kernel has already been rolled back, do not reflash it to obtain
this image. Report the recovery/rollback outcome instead.

The readback allows checking the kernel actually installed, header and
device tree, plus whether the OrangeFox ramdisk was retained. An empty
pstore directory leaves the early boot failure unconfirmed even when
offline packaging checks pass.

## 1. Enter recovery and preserve the evidence

Enter the bootloader and select Recovery Mode. If the installed recovery
also fails to start, temporarily boot the known-working OrangeFox image
you used previously, using its actual filename:

```bat
fastboot boot your-working-OrangeFox.img
```

This boots the image temporarily; it does not flash a recovery partition.
Do not use a recovery image for another device.

With OrangeFox running, use Windows CMD in your platform-tools directory:

```bat
adb devices
adb pull /sys/fs/pstore pstore
adb pull /tmp/recovery.log recovery.log
adb shell ls -l /sdcard/WireShark-backups
adb pull /sdcard/WireShark-backups WireShark-backups
```

Collect pstore before additional Android boot attempts. If the directory is
empty, keep the command output: absence of a saved panic does not prove
the kernel reached userspace. If recovery has not mounted pstore, inspect
`adb shell mount` and mount it from recovery's root shell:

```bat
adb shell "mount -t pstore pstore /sys/fs/pstore"
adb pull /sys/fs/pstore pstore
```

An "already mounted" error does not prevent reading the files.
If recovery exposes `/proc/last_kmsg`, also pull it:

```bat
adb pull /proc/last_kmsg last_kmsg.txt
```

If storage is encrypted, unlock/mount Data in OrangeFox to access the backups.
Do not format Data to obtain them. If backups cannot be accessed, use boot
and DTBO images from the **exact installed ROM build**.

## 2. Restore the slot that was flashed

The installer records its backup path on screen as:

```text
/sdcard/WireShark-backups/<timestamp>-<pid>_a/
/sdcard/WireShark-backups/<timestamp>-<pid>_b/
```

Choose the backup directory created by the failed installation. Do not
automatically choose the newest directory if you retried the installation:
a later backup may already contain the failing kernel. Confirm the folder
suffix and the boot/DTBO filenames match the slot shown in the installation
log. Expected full backup sizes are 67,108,864 bytes for boot and 8,388,608
bytes for DTBO on the normal floral layout.

After saving the files:

```bat
adb reboot bootloader
fastboot getvar current-slot
```

Check that the current slot matches the slot of the failed installation.
Repeated boot failures can cause the bootloader to select another slot.
If they differ, record that output and obtain guidance before changing the
active slot or writing a partition.

Open CMD **inside the chosen backup folder on your PC**. Ensure
`fastboot.exe` is available on PATH, or replace `fastboot` below with its
full executable path. The following is an example **only for slot b**,
with a matching `_b` backup:

```bat
fastboot flash boot_b boot_b.img
fastboot flash dtbo_b dtbo_b.img
```

For a matching slot-a installation/backup, use `boot_a boot_a.img` and
`dtbo_a dtbo_a.img` instead. Flash only that slot. If either command fails,
do not continue to reboot; retain the output.

After both commands report success:

```bat
fastboot reboot
```

Do not use an older WireShark ZIP as the rollback: neither previous ZIP has
a confirmed successful phone boot. Restoring both original images also
restores the original device-tree pairing.

## 3. Diagnostics needed for a supported fix

Provide:

- If still available, the actual failed boot partition image as described above.
- The flashed ZIP filename and `recovery.log` (including slot and backup path).
- All files pulled from `/sys/fs/pstore`, particularly console/dmesg ramoops.
- Whether restoring both pre-flash images made the ROM boot again.

If pstore is empty, further useful evidence is the failed boot partition image,
the pre-flash boot/DTBO images and the ROM's complete
`/vendor/lib/modules` directory. Obtain these from recovery using the
verified flashed slot; do not infer the slot from a different boot attempt.
A recovery `dmesg` describes the recovery kernel and must not be mistaken
for the kernel log from the failed Android boot.

## Investigation already completed

- The new and previous corrected artifact contain byte-identical DTB,
  DTBO, AnyKernel core and magiskboot payloads. This does not establish
  that those payloads are correct for the installed ROM.
- The latest source change restores normal rejection of incorrect module
  symbol CRCs. It is a possible regression point if additional installed
  ROM modules were not covered by the ZIP's preflight; it has not been
  identified as the cause.
- The reported failing kernel was built with AOSP Clang 12; the user's earlier
  `/proc/version` identifies their ROM kernel as Clang 22. Matching
  symbol CRCs and presence of legacy CFI alone do not prove every
  callback/type or runtime driver interaction is compatible.
- Initial independent validation had only the ADSP ROM module. The
  subsequently provided vendor archive covers all 27 built references and
  passes against both the reported failing build and the new diagnostic
  build. Runtime driver interactions remain untested.
- CFI remains enforcing and CRC checks remain enabled. Disabling them
  without diagnosing the failure would hide incompatibility, not establish
  a bootable kernel.

References: [AOSP A/B slot handling](https://source.android.com/docs/core/ota/ab/ab_implement)
and [Linux ramoops/pstore](https://www.kernel.org/doc/html/latest/admin-guide/ramoops.html).
