---
name: firmware-toolchain
description: Build, flash, and debug embedded firmware — ESP-IDF, PlatformIO, Arduino CLI, esptool, partition/OTA layouts, and bootlog forensics.
triggers:
  - "flash firmware"
  - "build firmware"
  - "compile firmware"
  - "esptool"
  - "platformio"
  - "pio run"
  - "arduino cli"
  - "esp-idf"
  - "idf.py"
  - "bootloader"
  - "partition table"
  - "ota update"
  - "serial monitor"
  - "upload error"
  - "guru meditation"
  - "esptool.py"
tools:
  - terminal
  - file_read
  - web_search
  - code_execution
---
# Tier-3 Firmware Build-Flash-Debug Protocol

When invoked for firmware build/flash/debug:

1. **Toolchain Selection.** ESP-IDF for native FreeRTOS control and version-pinned production builds (`idf.py set-target esp32 && idf.py build flash monitor`); PlatformIO for multi-board projects and CI (`pio run -e <env>`, `pio run -t upload`, `pio device monitor`); Arduino CLI/core for prototyping and library availability. State the chosen toolchain and exact version pins before generating code — register/enum layouts differ across IDF minor versions.

2. **Flash & Recovery.**
   - Standard: `esptool.py --chip esp32 --port COMx --baud 921600 --before default_reset --after hard_reset write_flash 0x0 <app.bin>` (offsets come from the partition table for IDF ≥4.x).
   - Bootloop recovery ladder: (1) hard reset, (2) hold BOOT/GPIO0 at reset to force download mode, (3) `erase_flash` then reflash full image, (4) `erase_region` on the suspect partition, (5) check flash mode/frequency matches module spec.
   - USB-serial bridges: CH340/CP210x/FT232 need OS drivers; native-USB boards (S3/C3) may expose two ports — use the one that appears at reset. On Linux add user to `dialout`, on Windows check Device Manager COM port.

3. **Partition Design.** Ship a reviewed `partitions.csv`: nvs (≥0x6000), phy_init, otadata, factory or app0/app1 for OTA (equal size), LittleFS/SPIFFS for assets, coredump partition for post-mortem. Never let app partitions be smaller than the built binary + headroom for growth; if OTA is enabled, validate `otadata` rollback and app-valid bits (`esp_ota_mark_app_valid_cancel_rollback`).

4. **Bootlog Forensics.**
   - Decode panics: `Guru Meditation Error: Core 0 panic'ed (LoadProhibited)` + backtrace → resolve addresses with `xtensa-esp32-elf-addr2line -pfiaC -e app.elf 0x40...` (esp32s3: `xtensa-esp32s3-elf-addr2line`; C3: `riscv32-esp-elf-addr2line`).
   - `Brownout detector was triggered` = supply sag under load → fix power section, not firmware.
   - Flash-cache errors pointing at ISR code → move handler to `IRAM_ATTR`. Task watchdog → longest-running task stack/loop audit, feed or restructure.
   - `rst:0x8 (TG1WDT_SYS_RESET)` / `rst:0x10 (RTCWDT_BROWN_OUT_RESET)` etc. — decode reset reason code, then chase root cause; never auto-reboot-mask a crash loop.

5. **FreeRTOS / Task Hygiene.** Stack sizing via `uxTaskGetStackHighWaterMark` under stress, not guesses. ISR rules: no blocking calls, no printf, keep handlers short + defer to queues. Watchdog: enable WDT on production tasks.

6. **Deliverables.** Exact command sequence from clean checkout to flashed device, partition CSV if touched, decoded-bootlog evidence for any claimed fix, and a rollback path if flashing remotely/OTA.

7. **Verification Gate.** Never declare "fixed" from a code-only argument — require a captured bootlog/monitor transcript or measured behavior proving the failure mode is gone.