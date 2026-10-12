# Offline API contract fixture. Never load Vivado or connect to hardware.
lassign $argv script fault bitfile backup
set events {}
proc event {name} {lappend ::events $name}
proc open_hw_manager {} {}
proc connect_hw_server {args} {}
proc get_hw_targets {args} {return target_0}
proc open_hw_target {args} {}
proc get_hw_devices {args} {return xc7a100t_0}
proc current_hw_device {args} {}
proc get_cfgmem_parts {args} {return mt25ql128-spi-x1_x2_x4}
proc create_hw_cfgmem {args} {}
proc create_hw_bitstream {args} {}
proc set_property {args} {}
proc refresh_hw_device {args} {}
proc close_hw_target {} {}
proc disconnect_hw_server {} {}
proc close_hw_manager {} {}
proc program_hw_devices {args} {
  event program_device
  if {$::fault eq "device_error"} {error "injected programming exception"}
  return xc7a100t_0
}
proc get_property {name device} {
  switch -- $name {
    PROGRAM.HW_CFGMEM {return cfgmem_0}
    PROGRAM.HW_CFGMEM_BITFILE {return bridge.bit}
    REGISTER.CONFIG_STATUS.BIT14_DONE_PIN {return [expr {$::fault ne "done_low"}]}
    REGISTER.CONFIG_STATUS.BIT04_END_OF_STARTUP_(EOS)_STATUS {return [expr {$::fault ne "eos_low"}]}
    REGISTER.CONFIG_STATUS.BIT00_CRC_ERROR {return [expr {$::fault eq "crc_error"}]}
    REGISTER.CONFIG_STATUS {return {DONE=1 EOS=1 CRC=0}}
    default {error "Unexpected property: $name"}
  }
}
proc readback_hw_cfgmem {args} {
  event readback
  if {$::fault eq "readback_error"} {error "injected readback exception"}
  set path [lindex $args [expr {[lsearch -exact $args -file]+1}]]
  set f [open $path wb]
  set bytes [expr {$::fault eq "short_backup" ? 127 : 16777216}]
  seek $f [expr {$bytes-1}]
  puts -nonewline $f "\0"
  close $f
  return ""
}
proc program_hw_cfgmem {args} {
  event program_flash
  if {$::fault eq "cfgmem_error"} {error "injected Flash verify exception"}
  return "Program and verification completed"
}
proc boot_hw_device {args} {event boot; return 1}

# Replace exit so source can report its result without killing this fixture.
rename exit fixture_exit
proc exit {args} {return}
set part mt25ql128-spi-x1_x2_x4
switch -- [file tail $script] {
  program_arty.tcl {set argv [list $bitfile]}
  backup_flash.tcl {set argv [list $part $backup]}
  program_flash.tcl {set argv [list $bitfile $part $backup]}
  default {error "Unexpected script"}
}
set argc [llength $argv]
set code [catch {source $script} message]
puts "MOCK_EVENTS $events"
if {$code} {
  puts "MOCK_FAILURE $message"
  fixture_exit 1
}
puts "MOCK_SUCCESS"
fixture_exit 0
