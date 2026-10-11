# Restored-ROM module baseline

On 2026-10-11, the maintainer supplied the complete `/vendor/lib/modules`
directory from the ROM that boots with the restored pre-flash boot image.
Archive SHA256: `6b076c8924445c5f11350d9c4ceadbf8c9822dc98da145d9b5fa3fcadef16788`.

All 27 module filenames match the built reference set in
`WireShark-floral-ad869a2e1f74.zip`. Running the package's host ABI checker
against every supplied module and the failed build's `Module.symvers`
passes 27/27. There are no missing reference modules. Checks include:

- ARM64 ELF format, module name, vermagic feature flags and module-structure size.
- All 2,555 imported symbol CRC records, including `module_layout`.
- Exported symbol names/counts and CRCs.
- Legacy-CFI mode compatibility.

An exploratory scan of ARM64 `__cfi_check` comparison constants finds
matching equality-comparison ID sets for 26/27 module pairs. Wi-Fi differs
in generated checks. Compiler transformations can change these sets, so
this scan cannot identify a CFI failure or replace a boot test.

Every supplied module's compiler metadata identifies Clang 22.0.2, build
`15071444`, matching the restored boot image. The named CFI type-ID symbol
sets also match the old references for all 27 modules, including Wi-Fi's
731 named type-ID symbols. This is a partial check: generated function
checks can differ even when those symbol names match.

Relocation inspection associates two differing Wi-Fi comparison IDs with
`qdf_vtrace_msg` and `qdf_trace_msg_cmn`:

| Function | ROM (Clang 22) | Failed-build reference (Clang 12) |
| --- | --- | --- |
| qdf_vtrace_msg | a55233600ebbea77 | a75ce6606d1ef09c |
| qdf_trace_msg_cmn | d685b5b4c2309c98 | 7a9b32b57420cb89 |

This establishes generated CFI metadata differences, without showing a
failing runtime call or proving that CFI caused the reported bootloop.
The ABI preflight's CFI-mode check does not compare these type IDs. The
fresh diagnostic comparison is recorded below.

These results rule out the mismatches checked by this preflight for the
uploaded modules. They do not establish runtime CFI correctness, correct
early kernel initialization, device-tree compatibility or phone bootability.
The recovery log contained no panic trace and pstore was empty.

## Fresh diagnostic comparison

[Run 38170155669](https://github.com/its-hecker/wireshark-kernel/actions/runs/38170155669) compiled the exact restored-ROM Clang 22
build with Full LTO. All 27 supplied ROM modules pass the fresh ABI
checker, including all 2,555 imported CRC records. There are no missing
reference modules. Named CFI type-ID sets and exploratory equality-comparison
ID sets match for all 27 module pairs. The earlier Wi-Fi comparison-ID
differences are absent in this scan.

This is stronger alignment with the working build profile, not a complete
runtime CFI proof or confirmation of the bootloop's cause. The compiled
configuration matches the supplied working kernel's configuration and the
embedded new-kernel config exactly.

The first device test uses a separately delivered coral temporary boot
image. Only its kernel was replaced; the compressed OrangeFox ramdisk,
original DTB and header settings were verified unchanged. No DTBO payload
or partition write is involved. See
[the temporary test guide](https://github.com/its-hecker/wireshark-kernel/blob/main/docs/boot-recovery.md#validated-temporary-diagnostic-image).

On 2026-10-12 (Asia/Karachi), the maintainer reported a Google-splash hang
and no ADB after the requested temporary test. The actual fastboot command
output is still needed to confirm the loaded image. This is a reported
failed device test, not a bootable fix; crash evidence is pending.
