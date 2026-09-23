# MicroPython board definition for the NeuroPico (RP2354A, 2 MB of flash in the chip).
# Build from the MicroPython tree with:
#   make -C ports/rp2 BOARD_DIR=<this directory>

# The NeuroPico has the same MCU and flash as the Seeed XIAO RP2350. The local
# header below reuses the SDK board file and pins the flash size explicitly.
list(APPEND PICO_BOARD_HEADER_DIRS ${MICROPY_BOARD_DIR})
set(PICO_BOARD "neuropico")
set(PICO_PLATFORM "rp2350")

# Flash layout. The file system takes the top 1 MiB, leaving 1 MiB for the
# firmware image and the frozen modules. The firmware only stores a small
# settings file and an error log, so it needs little space.
set(PICO_FLASH_SIZE_BYTES 2097152)
set(MICROPY_HW_FLASH_STORAGE_BYTES 1048576)

# Freeze the VertiGate application and its libraries into the image.
set(MICROPY_FROZEN_MANIFEST ${MICROPY_BOARD_DIR}/manifest.py)
