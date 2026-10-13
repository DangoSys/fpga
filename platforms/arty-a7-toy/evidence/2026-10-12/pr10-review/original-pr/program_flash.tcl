# Explicit nonvolatile programming: backs up Flash, then erases/programs/verifies.
if {$argc!=3} {error "Usage: program_flash.tcl image.mcs FLASH_PART fresh-backup.bin"}
lassign $argv image part backup
set image [file normalize $image]
set backup [file normalize $backup]
if {![file isfile $image]} {error "Missing Flash image"}
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
if {[file size $backup]!=16777216} {error "Incomplete backup; programming cancelled"}
puts "PASS FLASH_BACKUP: $backup bytes=16777216"
set_property PROGRAM.ADDRESS_RANGE use_file $memory
set_property PROGRAM.FILES [list $image] $memory
set_property PROGRAM.BLANK_CHECK 0 $memory
set_property PROGRAM.ERASE 1 $memory
set_property PROGRAM.CFG_PROGRAM 1 $memory
set_property PROGRAM.VERIFY 1 $memory
set_property PROGRAM.CHECKSUM 0 $memory
if {![program_hw_cfgmem $memory]} {error "Flash program/verify failed"}
puts "PASS FLASH_PROGRAM_VERIFY: $part $image"
# JP1 must be shorted; this reloads the FPGA from Flash without downloading .bit.
boot_hw_device -timeout 60 $device
refresh_hw_device $device
if {[get_property REGISTER.CONFIG_STATUS.BIT14_DONE_PIN $device]!=1 ||
    [get_property REGISTER.CONFIG_STATUS.BIT04_END_OF_STARTUP_(EOS)_STATUS $device]!=1 ||
    [get_property REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR $device]!=0} {
  error "FPGA did not successfully reconfigure from Flash"
}
puts "FLASH_BOOT_CONFIG_STATUS [get_property REGISTER.CONFIG_STATUS $device]"
close_hw_target
disconnect_hw_server
close_hw_manager
exit
