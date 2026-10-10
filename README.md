# WireShark kernel — Pixel 4 XL

Build and package the kernel source in this repository as an AnyKernel3 ZIP for **coral only**. The default source branch is `cnb-optimized`; select `cnb` under Run workflow to build the unchanged baseline. KernelSU settings come from the source's `floral_defconfig`; the resolved build config is included with every successful artifact.

The initial optimization set adapts three Sultan suspend/wakeup fixes: detect wakeups even when freezing just completed, preserve wakeups from suspend callbacks, and avoid repeated s2idle wake calls. Source details and host regression tests are in the kernel branch's `docs/wireshark-optimization.md` and `tests/suspend_wakeup_host.py`. CPU/GPU clocks, thermal controls and scheduler are unchanged. The optimized branch enables the kernel's supported ThinLTO mode to reduce linker pressure on hosted runners; CFI and shadow call stack remain enabled. No battery or frame-time improvement is claimed until measured on hardware.

**Known feature limitation:** the pinned KernelSU-Next revision `7d7f214e53d1b229115f094be4fe714601313027` does not define the SUSFS Kconfig options. Although the kernel source contains SUSFS code and defconfig entries, configuration normalization drops those options, so **SUSFS is inactive in the current build**. Enabling it requires a compatible KernelSU/SUSFS integration; a successful compile does not establish SUSFS support.

## Repository layout

- `main`: build workflows, AnyKernel3 installer, packaging and validation scripts.
- `cnb`: complete baseline kernel source.
- `cnb-optimized`: complete kernel source with the initial Sultan suspend/wakeup adaptations and ThinLTO enabled.

The workflow imports pinned source trees once, preserving licenses, KernelSU submodule references and optimization attribution. Existing source branches are never overwritten on subsequent runs. Both build choices clone this repository; further kernel development belongs on `cnb-optimized`.

## Build

Open **Actions → Build WireShark → Run workflow**, or push a build-script change to main. Download the `WireShark-coral` artifact when the run succeeds. Extract the outer GitHub artifact ZIP: the inner `WireShark-coral-<commit>.zip` is the flashable ZIP. A SHA256 file, source/tool provenance, build config, and matching module archive are included alongside it.

The first build is experimental until tested on a phone. This is not a universal Android 17 kernel. The Android 13 AOSP Coral kernel build workspace supplies the original build tools; the Wi-Fi and touch drivers are built from the bundled kernel source, ROM compatibility depends on the ROM's kernel/module ABI, not its Android version alone.

The corrected installer was built successfully in [run 38093277412](https://github.com/its-hecker/wireshark-kernel/actions/runs/38093277412), using builder commit `ef4a0966f127ff03437711d0041d8161d8d86104` and source `4919641578c86a0463b1de5ccc1de80d429cfd8c` (`cnb-optimized`). [Download the WireShark-coral artifact](https://github.com/its-hecker/wireshark-kernel/actions/runs/38093277412/artifacts/11685965949) and extract `WireShark-coral-4919641578c8.zip`. Its SHA256 is `9df1d3d0e7c4246cf02449537be38313f4d2ac670bc848e3d225c3e385033872`.

Verification passed: 18 host/preflight regression cases, all 27 built reference-module checks, ZIP/reference integrity and a static ARM64 checker with no dynamic-loader dependency. The uploaded InfinityX `adsp_loader_dlkm.ko` passes the checker against this build's actual exports, including all 28 imported CRCs; `__stack_chk_guard` is exported with CRC `0x8f678b07`. The remaining installed ROM modules are checked during installation. Phone flashing and boot testing remain pending.

## Installation

Use an unlocked Pixel 4 XL and a recovery or root kernel installer that supports AnyKernel3. Keep a known-good boot image and a way to restore it with fastboot. Flash the inner ZIP on the compatible ROM, then reboot.

The installer checks `coral`, determines the active A/B slot, backs up its boot and dtbo partitions to `/sdcard/WireShark-backups`, and repacks the existing boot image while preserving its ramdisk. It installs the built kernel, DTB and DTBO only into the active slot. It does not wipe data or flash the other slot.

**Module ABI preflight runs before any partition write.** Every module built with this kernel must be readable on the installed ROM. A static ARM64 checker compares its module name, vermagic, module structure size and legacy Clang CFI mode with the built reference. It checks every imported symbol CRC against the freshly built kernel's complete `Module.symvers`, and checks the module's exported symbol names and CRCs against its reference. An additional compiler-generated import is accepted only when its symbol and CRC exist in the target build. A whole-file SHA256 difference is no longer an installation failure; SHA256 still verifies the reference files inside the package.

Missing or unreadable modules produce a Vendor-mount diagnostic; actual ABI failures report the incompatible symbol or metadata. Vendor is only read, and the ZIP does not replace the ROM's modules. Reference `.ko` files in `module-reference/` are used for validation only. The separate matching module archive remains available for ROM developers. Passing this preflight is not a hardware boot test or a guarantee that all driver behavior is compatible.

The original OrangeFox abort on InfinityX was caused by the exact-hash rule. The supplied Clang 22.0.2 `adsp_loader_dlkm.ko` and the Clang 12.0.5 reference have the same vermagic, 896-byte module structure and all 27 shared import CRCs. The ROM driver additionally imports `__stack_chk_guard`, which this source exports. The new checker verifies that import against the actual build exports rather than assuming that a compiler difference is an ABI failure.

Backups are partition images, not data backups. To restore boot use `fastboot flash boot_a <backup>` or `boot_b`, matching the recorded slot; similarly restore `dtbo_a` or `dtbo_b` if needed. Never flash an image from a different device or ROM.

## Sources and licensing

- Kernel source: this repository's `cnb` and `cnb-optimized` branches (GPL-2.0 and source-specific notices)
- Import origin: https://github.com/its-hecker/infinity_cnb_kernel_google_msm-4.14; exact source revisions are recorded in `scripts/import-source.sh` and the import commits
- KernelSU-Next: the source repository's pinned submodule
- Build manifest: https://android.googlesource.com/kernel/manifest/ branch `android-msm-coral-4.14-android13`
- Installer: https://github.com/osm0sis/AnyKernel3 (upstream license retained in ZIP)

Build output records exact kernel, submodule, manifest-project and installer revisions. Consult the original source repositories for their licenses.

