# Restored-ROM diagnostic source

This branch starts from `ad869a2e1f74090fea2ff402d1261e9206ba13cd` and changes
the floral defconfig from ThinLTO to Full LTO to match the configuration
extracted from the working pre-flash boot image. CFI, shadow call stack,
module CRC rejection and the suspend/wakeup changes remain enabled.

Compiler pinning, workflow instructions and validation results are maintained
in the builder branch:
https://github.com/its-hecker/wireshark-kernel/blob/boot-diagnostic-builder/docs/diagnostic-profile.md

All 27 uploaded ROM modules passed the reported failing build's static ABI
checks. This does not identify the boot failure or verify a phone boot.
Keep the restored kernel installed until a diagnostic image has been built
and validated. The first planned phone test uses a temporary boot image
preserving the working ramdisk and device trees.
