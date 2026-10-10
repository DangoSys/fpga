# Standalone DDR-controller resource measurement; does not create a board bit.
set root [file dirname [file dirname [file normalize [info script]]]]
set_param general.maxThreads 4
open_project $root/build/mig/arty_linux_mig.xpr
synth_ip [get_ips arty_ddr3]
set checkpoint [file join $root build mig arty_linux_mig.gen sources_1 ip arty_ddr3 arty_ddr3.dcp]
if {![file exists $checkpoint]} {error "MIG synthesis did not produce its checkpoint"}
close_project
open_checkpoint $checkpoint
report_utilization -file $root/build/mig/utilization.rpt
report_drc -file $root/build/mig/drc.rpt
