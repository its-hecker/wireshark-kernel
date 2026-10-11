# Lineage-based ROMs on coral and flame

The floral defconfig and Google device-tree Makefile cover Pixel 4 XL
(coral) and Pixel 4 (flame). Preserve the full DTBO table and ordering,
including prototype, EVT, DVT and production overlays for both devices.
Production board IDs are 0x051e05 (coral) and 0x061e05 (flame).

Configuration comparison used LineageOS lineage-24.0 kernel commit
28f9290ae067d3e7857126eb6312720dbe9c7c80. Baseline floral settings match;
WireShark adds ThinLTO, WireGuard and its existing KernelSU integration.
The Lineage device tree at 6a4ad9f39145ba7c6ff927041b6e9ff453edc1f8
uses floral_defconfig, boot header v2, a DTB in boot and an 8 MiB DTBO
partition on both devices. This is a source comparison, not a ROM binary
ABI or hardware boot test.

kernel/module.c::same_magic ignores the release name for versioned
modules. The ZIP preflight follows this rule and still requires matching
vermagic feature flags, module layout, imported/exported CRCs and legacy
Clang CFI mode. Missing/incompatible required modules prevent flashing.

The optimized source restores rejection of mismatched CRCs in
check_version; it no longer logs a mismatch and accepts the module.
tests/module_loader_host.py compiles the actual function bodies and
exercises 8 cases. The unchanged cnb baseline is retained separately.

Target Android 17 Lineage-based ROMs must have a matching module ABI.
Phone boot, Wi-Fi, audio, camera, touch and suspend testing remain needed
on both devices and each ROM family. A changed driver ABI needs an adapted
build; skipping the compatibility checks does not fix that mismatch.
