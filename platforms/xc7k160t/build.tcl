set top "DigitalTop"
set part "xc7k160tffg676-2"
set clk_period 10.0
set verilog_dir "/home/zx/buckyball/arch/build/sims.p2e.P2EPebbleLinuxConfig"
set xdc_file "../constraints/pin.xdc"
set output "buckyball_top"

set sv_count 0
foreach f [glob -nocomplain ${verilog_dir}/*.sv] {
	read_verilog -sv $f
	incr sv_count
}
puts "Total $sv_count .sv file"
set v_count 0
read_verilog -sv dpi_stubs.sv
foreach f [glob -nocomplain ${verilog_dir}/*.v] {
	if {[string match "*DPI*" $f] || [string match "*plusarg_reader*" $f]} {
                continue
        }
	read_verilog -sv $f
        incr v_count
}
puts "Total $v_count .v file"

if {[file exists $xdc_file]} {
 	read_xdc $xdc_file
} else {
	puts "WARNING: no xdc, synthesis-only"
}
synth_design -top $top -part $part
report_utilization -hierarchical -file util_hier.rpt
if {[get_ports -quiet *uncore_clock] ne ""} {
	create_clock -period $clk_period -name clk [get_ports *uncore_clock]
}

opt_design
place_design
route_design
write_bitstream -force ${output}.bit
write_checkpoint -force ${output}.dcp
report_utilization    -file ${output}_utilization.rpt
report_timing_summary -file ${output}_timing.rpt
report_power          -file ${output}_power.rpt
puts "=== BUILD COMPLETE ==="
