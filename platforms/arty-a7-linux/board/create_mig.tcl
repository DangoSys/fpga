# Generate only the official Rev E.0 controller. This does not program hardware.
# The physical board revision must be verified before a board release.
set root [file dirname [file dirname [file normalize [info script]]]]
create_project arty_linux_mig $root/build/mig -part xc7a100tcsg324-1 -force
create_ip -name mig_7series -vendor xilinx.com -library ip -version 4.2 -module_name arty_ddr3
set_property CONFIG.XML_INPUT_FILE [file join $root board vendor mig.prj] [get_ips arty_ddr3]
generate_target all [get_ips arty_ddr3]
report_ip_status -file $root/build/mig/ip_status.rpt
close_project
