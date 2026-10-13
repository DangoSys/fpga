set root [file dirname [file dirname [file normalize [info script]]]]
cd $root
if {[llength $argv]<1 || [llength $argv]>2} {error "Usage: build_board.tcl OUTPUT_DIRECTORY ?flash?"}
set flash 0
if {[llength $argv]==2} {
  if {[lindex $argv 1] ne "flash"} {error "Second argument must be flash"}
  set flash 1
}
set out [file normalize [lindex $argv 0]]
file mkdir $out
file mkdir $out/ip
proc phase {name} {
  global out
  set f [open $out/phase.txt w];puts $f $name;close $f
  puts "BOARD_PHASE $name"
}
set_param general.maxThreads 8
phase CREATE_IP
create_project -in_memory -part xc7a100tcsg324-1
set_property target_language Verilog [current_project]
create_ip -name mig_7series -vendor xilinx.com -library ip -version 4.2 -module_name arty_ddr3 -dir $out/ip
set_property CONFIG.XML_INPUT_FILE $root/board/vendor/mig.prj [get_ips arty_ddr3]
create_ip -name axi_clock_converter -vendor xilinx.com -library ip -version 2.1 -module_name toy_axi_cdc -dir $out/ip
set_property -dict {CONFIG.PROTOCOL AXI4 CONFIG.ADDR_WIDTH 28 CONFIG.DATA_WIDTH 128 CONFIG.ID_WIDTH 4 CONFIG.ACLK_ASYNC 1 CONFIG.SYNCHRONIZATION_STAGES 3} [get_ips toy_axi_cdc]
generate_target all [get_ips]
report_ip_status -file $out/ip-status.rpt
phase SYNTH_IP
synth_ip [get_ips]
phase SYNTH_BOARD
if {$flash} {read_verilog -sv $root/build/flash-boot/ToyLinuxChip.sv} else {
  read_verilog -sv $root/build/serial-bound/ToyLinuxChip.sv
}
read_verilog -sv $root/build/serial-bound/FpgaMemories.sv
foreach f [glob $root/board/*.sv] {read_verilog -sv $f}
set_property verilog_define {SYNTHESIS BUCKYBALL_DISABLE_DPI} [current_fileset]
read_xdc $root/board/arty_a7.xdc
read_xdc $root/board/flash_boot.xdc
synth_design -top toy_a7_top -part xc7a100tcsg324-1 -flatten_hierarchy rebuilt -directive AreaOptimized_high -resource_sharing on -generic FLASH_BOOT=$flash
write_checkpoint -force $out/synthesized.dcp
report_utilization -file $out/synth-utilization.rpt
report_utilization -hierarchical -file $out/synth-hierarchy.rpt
report_timing_summary -delay_type min_max -file $out/synth-timing.rpt
set unresolved [get_cells -hier -quiet -filter {IS_BLACKBOX == 1}]
if {[llength $unresolved]} {error "Unresolved black boxes: $unresolved"}
phase OPTIMIZE
opt_design -directive ExploreArea
write_checkpoint -force $out/optimized.dcp
report_utilization -file $out/opt-utilization.rpt
phase PLACE
place_design -directive Explore
write_checkpoint -force $out/placed.dcp
phase PHYS_OPT
phys_opt_design -directive Explore
phase ROUTE
route_design -directive Explore
write_checkpoint -force $out/routed.dcp
phase REPORT
report_utilization -file $out/routed-utilization.rpt
report_utilization -hierarchical -file $out/routed-hierarchy.rpt
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -file $out/routed-timing.rpt
report_route_status -file $out/route-status.rpt
report_drc -file $out/drc.rpt
set cdc [report_cdc -details -return_string]
set f [open $out/cdc.rpt w];puts $f $cdc;close $f
set skew [report_bus_skew -return_string]
set f [open $out/bus-skew.rpt w];puts $f $skew;close $f
report_methodology -file $out/methodology.rpt
report_io -file $out/io.rpt
report_clocks -file $out/clocks.rpt
check_timing -verbose -file $out/check-timing.rpt
if {[regexp {CDC-[0-9]+\s+Critical} $cdc]} {error "Critical CDC findings; see cdc.rpt"}
if {[string match *VIOLATED* $skew]} {error "Bus skew failed; see bus-skew.rpt"}
foreach kind {max min} {
  set paths [get_timing_paths -delay_type $kind -max_paths 1]
  if {[llength $paths]==0} {error "Missing $kind timing paths"}
  if {[get_property SLACK [lindex $paths 0]]<0} {error "$kind timing failed"}
}
if {![report_route_status -boolean_check ROUTED_FULLY]} {error "Routing incomplete"}
if {[report_route_status -boolean_check ERRORS_IN_ROUTES]} {error "Routing errors"}
set errors [get_drc_violations -quiet -filter {SEVERITY == Error || SEVERITY == {Critical Warning}}]
if {[llength $errors]} {error "DRC errors/critical warnings: $errors"}
phase BITSTREAM
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
write_bitstream -force $out/toy_a7.bit
phase COMPLETE
puts "PASS BOARD_PLACE_ROUTE_TIMING_BITSTREAM: engineering Rev E target; flash=$flash; this build does not validate physical boot"
