# Recovering from the reported WireShark boot failure

## Affected artifact and current status

On 2026-10-11, a user reported that their phone stayed at the Google logo
after flashing the newly delivered floral kernel. The expected artifact is
`WireShark-floral-ad869a2e1f74.zip` from
[run 38161422852](https://github.com/its-hecker/wireshark-kernel/actions/runs/38161422852).
Confirm the actual flashed filename in the recovery log before attributing
the report to this exact build. No failed-boot crash log or boot image has
been supplied yet, so the root cause remains unconfirmed.

Do not flash this artifact again or wipe data to resolve this kernel failure.
The installer changes only boot and DTBO in the selected slot. Restore the
pre-flash images from the same device/ROM.

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
- The new kernel is built with AOSP Clang 12; the user's earlier
  `/proc/version` identifies their ROM kernel as Clang 22. Matching
  symbol CRCs and presence of legacy CFI alone do not prove every
  callback/type or runtime driver interaction is compatible.
- The installer checked the 27 modules built by this configuration,
  not every driver that the installed ROM might load. Local independent
  validation had access to only one actual ROM module (ADSP).
- CFI remains enforcing and CRC checks remain enabled. Disabling them
  without diagnosing the failure would hide incompatibility, not establish
  a bootable kernel.

References: [AOSP A/B slot handling](https://source.android.com/docs/core/ota/ab/ab_implement)
and [Linux ramoops/pstore](https://www.kernel.org/doc/html/latest/admin-guide/ramoops.html).
