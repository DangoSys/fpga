# Read all existing Flash before any erase. This temporarily replaces FPGA SRAM
# with Vivado's SPI bridge, but never requests a Flash write/erase.
if {$argc!=2} {error "Usage: backup_flash.tcl FLASH_PART output.bin"}
lassign $argv part backup
set backup [file normalize $backup]
if {[file exists $backup]} {error "Refusing to overwrite an existing backup"}
if {$part ni {s25fl128sxxxxxx0-spi-x1_x2_x4 s25fl128sxxxxxx1-spi-x1_x2_x4 mt25ql128-spi-x1_x2_x4}} {
  error "Select the exact supported 128-Mbit Arty Flash model"
}
open_hw_manager
connect_hw_server -allow_non_jtag
set targets [get_hw_targets -quiet]
if {[llength $targets]!=1} {error "Expected one attached JTAG target"}
open_hw_target [lindex $targets 0]
set devices [get_hw_devices -quiet -filter {PART == xc7a100t}]
if {[llength $devices]!=1} {error "Expected one XC7A100T"}
set device [lindex $devices 0]
current_hw_device $device
set choices [get_cfgmem_parts -of_objects $device -filter "NAME == $part"]
if {[llength $choices]!=1} {error "Flash part is not uniquely compatible with this FPGA"}
create_hw_cfgmem -hw_device $device [lindex $choices 0]
set memory [get_property PROGRAM.HW_CFGMEM $device]
create_hw_bitstream -hw_device $device [get_property PROGRAM.HW_CFGMEM_BITFILE $device]
program_hw_devices $device
file mkdir [file dirname $backup]
readback_hw_cfgmem -all -file $backup -format bin $memory
if {[file size $backup]!=16777216} {error "Incomplete Flash backup"}
puts "PASS FLASH_BACKUP: $part $backup bytes=16777216"
close_hw_target
disconnect_hw_server
close_hw_manager
exit
