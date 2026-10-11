# Restored-ROM module baseline

On 2026-10-11, the maintainer supplied the complete `/vendor/lib/modules`
directory from the ROM that boots with the restored pre-flash boot image.
Archive SHA256: `6b076c8924445c5f11350d9c4ceadbf8c9822dc98da145d9b5fa3fcadef16788`.

All 27 module filenames match the built reference set in
`WireShark-floral-ad869a2e1f74.zip`. Running the package's host ABI checker
against every supplied module and the failed build's `Module.symvers`
passes 27/27. There are no missing reference modules. Checks include:

- ARM64 ELF format, module name, vermagic feature flags and module size.
- Every imported symbol CRC, including `module_layout`.
- Exported symbol names/counts and CRCs.
- Legacy-CFI mode compatibility.

An exploratory scan of ARM64 `__cfi_check` comparison constants finds
matching equality-comparison ID sets for 26/27 module pairs. Wi-Fi differs
in generated checks. Compiler transformations can change these sets, so
this scan cannot identify a CFI failure or replace a boot test.

These results rule out the mismatches checked by this preflight for the
uploaded modules. They do not establish runtime CFI correctness, correct
early kernel initialization, device-tree compatibility or phone bootability.
The recovery log contained no panic trace and pstore was empty.

Next: build with the exact restored-ROM compiler and Full LTO, repeat all
module checks, then prepare a temporary boot image containing only the new
kernel. Preserve the uploaded working boot image's ramdisk and DTB and
leave the on-device DTBO unchanged during that first device test.

No phone test of the diagnostic image has yet been performed.
