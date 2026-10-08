# WireShark optimization: suspend/wakeup set 1

Branch: `cnb-optimized`, based on `cnb` commit `e8d36b72ab353f841892cd64b7ad20491f5479d5`.

This first set adapts three fixes by Sultan Alsawaf from the Pixel 4/XL kernel (`kerneltoast/android_kernel_google_floral`, `11.0.0-sultan`):

1. `ffd7943b5013cb63143106063f451212f83ddfe2`: check a pending wakeup before treating task freezing as complete, and return `-EBUSY` when a wakeup aborted freezing, even when the remaining task count is zero.
2. `72b078af900a`: clear stale wakeup state before suspend preparation callbacks rather than later in `freeze_processes()`, preserving wakeups raised by those callbacks.
3. `851f9989ed16`: call `s2idle_wake()` only for the transition to the first pending suspend abort. This adaptation uses the fully ordered `atomic_inc_return()` rather than Sultan's relaxed operation, retaining conservative memory ordering.

These fixes target unnecessary suspend work and wake responsiveness. They do not establish a measured battery or frame-rate gain. The scheduler, memory subsystem, CPU/GPU clocks, thermal controls, CFI and KernelSU settings are unchanged. SUSFS source entries are retained; its existing integration limitation is described below. This is not a complete Sultan kernel port.

Source changes were reviewed against the current implementations. A host regression harness exercises the modified task-freezing function and verifies the wakeup handling, including wakeups with zero remaining tasks. The hosted kernel build and ZIP validation subsequently passed; hardware validation remains required.

Before daily use, compare with the baseline on the same ROM: repeated screen-off/on, deep sleep overnight, charger plug/unplug, calls, alarms, USB, camera, Wi-Fi and Bluetooth. Review suspend errors and pstore after unexpected reboots. Measure idle drain over several comparable runs; do not infer gains from a successful build alone.

The flashable ZIP keeps its module compatibility checks. If those fail, the ROM must be rebuilt with this branch and its matching modules before installation.

## Hosted build configuration

After the initial full-LTO build was terminated during linking by a runner shutdown, `floral_defconfig` now enables the existing `CONFIG_THINLTO` implementation. Clang LTO, CFI and Shadow Call Stack remain enabled. This reduces the cost of whole-kernel linking; it is a build configuration change, not a measured runtime optimization. Matching modules must be built with this configuration, and the ZIP's module checks remain active.

Credit: Sultan Alsawaf <sultan@kerneltoast.com>. Original commit messages and source history are available at https://github.com/kerneltoast/android_kernel_google_floral.

## Verified build and feature limitation

The hosted optimized build succeeded at https://github.com/its-hecker/wireshark-kernel/actions/runs/37784650703 using source commit `332ebd1b8867ce3cd8f3fb8943d338d7885a4328`. The downloaded artifact confirms ThinLTO, CFI, shadow call stack and KernelSU/manual hooks. All 27 built module hashes match the flashable ZIP's manifest. This verifies compilation and packaging, not boot behavior or battery/performance gains.

The existing KernelSU-Next submodule pin `7d7f214e53d1b229115f094be4fe714601313027` has no SUSFS Kconfig definitions. The retained SUSFS defconfig entries are therefore dropped during normalization; SUSFS is inactive in this artifact. Enabling SUSFS requires a compatible integration rather than only defconfig changes. This limitation also applies to the baseline using the same submodule pin.
