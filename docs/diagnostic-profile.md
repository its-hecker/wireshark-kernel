# Restored-ROM diagnostic build profile

The phone boots again after restoring its pre-flash boot backup. Keep that
working kernel installed while comparing the full ROM module set. The boot
failure has not been tied to a confirmed kernel panic.

The uploaded pre-flash image identifies Clang 22.0.2, AOSP r596125, build
15071444 and LLVM commit de03d430485c884861198b25459851f429cbdbad.
Its extracted configuration uses Full LTO; the failed build used Clang 12
and ThinLTO. Matching the known working profile is a diagnostic step,
not proof that either difference caused the failed boot.

- Source branch: `cnb-boot-diagnostic`, based on `ad869a2e1f74090fea2ff402d1261e9206ba13cd`.
  Only the floral defconfig LTO selection changes. Suspend optimizations,
  CFI, shadow call stack and strict module CRC rejection remain.
- Builder branch: `boot-diagnostic-builder`. The workflow is manual only.
  It has not been built or verified on a phone.
- Toolchain repository: https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86
- Pinned repository commit: `6d497adf6103f63e788baef87e8f9d05b651656f`.
- Selected directory: `clang-r596125`, explicitly overriding the old Coral
  workspace compiler. Build stops if the compiler identity does not match.
- Artifacts include compiler version and toolchain provenance in addition
  to the source/builder metadata. Artifact label is `WireShark-floral-diagnostic`.

Next required evidence is the actual ROM's complete `/vendor/lib/modules`
directory. The earlier independent module validation had only ADSP.
Compare all those modules against fresh exports and CFI metadata before
preparing any further device test. Do not reinstall the reported failing
ZIP just to collect logs. A future test should first use a temporary boot
image preserving the installed recovery ramdisk and original device trees.

Primary toolchain reference:
https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/refs/heads/mirror-goog-main-llvm-toolchain-source
