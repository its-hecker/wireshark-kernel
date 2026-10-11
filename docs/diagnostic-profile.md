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
- Builder branch: `boot-diagnostic-builder`. The workflow accepts manual
  runs and builds changes to build/installer files on this branch only.
  A successful CI build is not phone boot verification.
- Toolchain repository: https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86
- Pinned repository commit: `9b144befdfd93b90e02c663504fb9f4b95f9faf8`.
  Its official commit message identifies build `15071444`, and the tree
  contains `manifest_15071444.xml`. The initially prepared pin pointed to
  a later compiler rebuild and was corrected before the first build.
- Selected directory: `clang-r596125`, explicitly overriding the old Coral
  workspace compiler. Build stops if the compiler identity does not match.
- Artifacts include compiler version and toolchain provenance in addition
  to the source/builder metadata. Artifact label is `WireShark-floral-diagnostic`.

The actual ROM's complete `/vendor/lib/modules` archive was received on
2026-10-11. All 27 modules pass the failed build's static ABI checker,
including imported/exported CRCs, vermagic feature flags, module layout,
and the presence of legacy CFI. This does not establish bootability.
An exploratory CFI comparison-ID scan matches 26 module reference sets;
Wi-Fi has generated-code differences requiring further inspection. The
scan is not a complete CFI verifier. See `rom-module-baseline.md`.
Compare all modules again against fresh exports before preparing any
further device test. Do not reinstall the reported failing
ZIP just to collect logs. A future test should first use a temporary boot
image preserving the installed recovery ramdisk and original device trees.

Primary toolchain reference:
https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+/refs/heads/mirror-goog-main-llvm-toolchain-source
