// SDK board header for the Dynamixel Controller. The board is electrically a Seeed XIAO
// RP2350 as far as the SDK is concerned: RP2350A, 2 MB QSPI flash, W25Q080
// boot stage 2. Only the pin usage differs, and MicroPython does not need that here.
#include "boards/seeed_xiao_rp2350.h"

// The cmake-level settings are read from this file by the build system, so
// they are repeated here. PICO_FLASH_SIZE_BYTES reaches the compiler from
// cmake as a command-line definition.
pico_board_cmake_set(PICO_PLATFORM, rp2350)
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (2 * 1024 * 1024))
pico_board_cmake_set_default(PICO_RP2350_A2_SUPPORTED, 1)
