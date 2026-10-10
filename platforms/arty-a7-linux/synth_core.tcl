# Resource feasibility for the COMPLETE original Pebble, including L2.
# This is an OOC checkpoint, never a downloadable board bitstream.
set root [file dirname [file normalize [info script]]]
cd $root
file mkdir build/synth
set_param general.maxThreads 8
create_project -in_memory -part xc7a100tcsg324-1
read_verilog -sv generated/PebbleLinuxChip.sv
set_property verilog_define {SYNTHESIS BUCKYBALL_DISABLE_DPI} [current_fileset]
read_xdc core.xdc
synth_design -top PebbleLinuxChip -part xc7a100tcsg324-1 -mode out_of_context
write_checkpoint -force build/synth/PebbleLinuxChip.dcp
report_utilization -file build/synth/utilization.rpt
report_utilization -hierarchical -file build/synth/hierarchy.rpt
report_timing_summary -file build/synth/timing.rpt
report_drc -file build/synth/drc.rpt
set blackboxes [get_cells -hier -filter {IS_BLACKBOX == 1}]
if {[llength $blackboxes] != 0} {error "Unresolved black boxes: $blackboxes"}
