# Volatile JTAG programming only. Usage:
# Confirm physical Rev E DDR compatibility before using this engineering image.
# vivado -mode batch -source board/program_arty.tcl -tclargs /path/to/toy_a7.bit
if {$argc != 1} { error "Supply the Arty A7-100T .bit file" }
set bitfile [file normalize [lindex $argv 0]]
if {![file isfile $bitfile]} { error "Bitstream not found: $bitfile" }
open_hw_manager
connect_hw_server -allow_non_jtag
set targets [get_hw_targets -quiet]
if {[llength $targets] != 1} {
  error "Expected one connected JTAG target. Select the Arty manually in Hardware Manager if multiple boards are attached."
}
open_hw_target [lindex $targets 0]
set devices [get_hw_devices -quiet -filter {PART == xc7a100t}]
if {[llength $devices] != 1} { error "Expected one XC7A100T; inspect the connected board" }
set device [lindex $devices 0]
current_hw_device $device
set_property PROGRAM.FILE $bitfile $device
if {[catch {program_hw_devices $device} message options]} {
  return -options $options "JTAG programming failed: $message"
}
refresh_hw_device $device
if {[get_property REGISTER.CONFIG_STATUS.BIT14_DONE_PIN $device]!=1 ||
    [get_property REGISTER.CONFIG_STATUS.BIT04_END_OF_STARTUP_(EOS)_STATUS $device]!=1 ||
    [get_property REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR $device]!=0} {
  error "JTAG configuration status rejected: expected DONE/EOS high and CRC error clear"
}
puts "ARTY_JTAG_PROGRAMMED: $bitfile"
close_hw_target
disconnect_hw_server
close_hw_manager
exit
