---
name: embedded-hardware
description: Board-level architecture and engineering for ESP32/ESP8266/STM32/RP2040/Arduino — pin muxing, power budgets, buses, wiring, boot modes, hardware bring-up.
triggers:
  - "esp32"
  - "esp8266"
  - "esp-s3"
  - "stm32"
  - "rp2040"
  - "arduino"
  - "pinout"
  - "gpio"
  - "wiring diagram"
  - "power budget"
  - "level shifter"
  - "skematik"
  - "desain pcb"
  - "sensor wiring"
  - "kabel rangkaian"
tools:
  - file_read
  - terminal
  - web_search
  - code_execution
---
# Tier-3 Embedded Board Architecture Protocol

When invoked for board/hardware engineering:

1. **Board Selection Matrix.** Before answering, resolve the MCU family trade space: ESP32 classic (dual-core Xtensa, BT Classic+BLE) vs S2 (single core, native USB, no BT) vs S3 (dual core, BLE+USB-OTG, AI vector ops) vs C3 (RISC-V single core, cheap, BLE) vs C6 (WiFi6+BLE5+Zigbee/Thread) vs H2 (Zigbee/Thread, no WiFi) vs ESP8266 (WiFi only, 1 ADC, no BT) vs STM32 (wide family, industrial timers/ADC) vs RP2040 (dual M0+, PIO, no radio). Justify selection against: RAM/PSRAM, flash size, native USB need, radio stack, GPIO count, price, power envelope.

2. **Pin Architecture Rules (ESP32 family).**
   - Strapping pins control boot: GPIO0 (LOW = download mode), GPIO45/46 (VDD/flash voltage), MTDI/GPIO12 (flash voltage — never pull HIGH at reset on WROVER/WROOM). Any peripheral wired to strapping pins must be inactive at boot.
   - Input-only pins: GPIO34-39 (no internal pull-ups — external resistors required).
   - ADC2 is unusable while WiFi is active — use ADC1 (GPIO32-39) for analog when WiFi runs. DAC: GPIO25/26. Touch: GPIO0/T1-GPIO14/T6 family-dependent.
   - On WROVER modules GPIO16/17 are reserved for PSRAM. On octal-PSRAM variants (S3 R8) GPIO35-37 reserved.
   - Prefer IOMUX-designated pins for high-speed SPI/I2S; GPIO matrix costs routing flexibility but handles lower rates.

3. **Power Design.** Compute the power budget explicitly: active TX bursts (WiFi ~160-260 mA peaks on ESP32), deep sleep (~10 µA modem-off, µA-class per datasheet), RTC peripherals. Rules:
   - Never feed boards through diode-dropped USB 5V alone with motors/relays on the same rail — brownout detector resets are the symptom, shared-impedance supply sag is the root cause. Separate supply rails + star grounding.
   - LiPo: TP4056 + protection cell, boost or LDO sized for TX peak (ME6211/RT9013 ≥500 mA; AMS1117 only above ~7 V headroom input).
   - Logic 3.3 V devices: level-shift 5 V signals (BSS138 bidirectional for I2C, TXS0108E/TXB0108 for push-pull buses). Never feed 5 V into non-5V-tolerant pins.
   - Inductive loads (relay/solenoid/motor): transistor sized for stall current + flyback diode across coil; prefer logic-level MOSFETs (AO3400/IRLZ44N) over 5 V-Arduino-dependent TIP120.

4. **Buses & Interfaces.**
   - I2C: external pull-ups 2.2-4.7 kΩ (internal ~45 kΩ is too weak for 400 kHz+); scan bus (`i2c.detect`) before trusting address tables; watch address conflicts; cable >30 cm = slow down or buffer (PCA9615 differential).
   - SPI: dedicated CS per device, keep clock under device spec at temperature/distance, consider DMA for displays/cameras.
   - UART: default console 115200 8N1 on UART0; reserve UART1/2 for GPS/RS485; RS485 (MAX485/automated direction) for industrial runs; CAN needs transceiver (SN65HVD230/TJA1050).
   - USB CDC (S2/S3/C3): enable `USB CDC On Boot` or lose console output.

5. **Bring-Up Checklist.** In order: (a) power rail voltage under load, (b) boot UART log before firmware, (c) flash with correct mode (dio/qio matches module), (d) verify brownout level vs measured rail, (e) probe each bus with logic analyzer or scope capture, (f) thermal check on regulators. Smoke = disconnect immediately, measure, do not iterate blindly.

6. **Deliverables.** Every design answer must include: exact GPIO map table (pin → function → constraints), ASCII connection diagram, power math (mA budget per state), and BOM with real part numbers.

7. **Sourcing.** Cite datasheet numbers, not blog folklore. When a claim is module-variant dependent (WROOM vs WROVER vs super-mini clones), state the variant explicitly.