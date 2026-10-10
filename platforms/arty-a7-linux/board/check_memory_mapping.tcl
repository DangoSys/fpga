# Validate the previously register-mapped D-cache array with its FPGA binding.
set root [file dirname [file dirname [file normalize [info script]]]]
cd $root
set out build/fpga-memory/bound/dcache-synth
file mkdir $out
create_project -in_memory -part xc7a100tcsg324-1
read_verilog -sv build/fpga-memory/bound/FpgaMemories.sv
synth_design -top bbtile_dcache_data_arrays_0_ext -part xc7a100tcsg324-1 -mode out_of_context
report_utilization -file $out/utilization.rpt
write_checkpoint -force $out/memory.dcp
if {[llength [get_cells -hier -filter {REF_NAME =~ RAMB*}]] == 0} {
  error "D-cache storage failed to map to block RAM"
}
if {[llength [get_cells -hier -filter {IS_BLACKBOX == 1}]] != 0} {
  error "Unresolved memory cells"
}
