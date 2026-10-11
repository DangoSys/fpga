# User pins from Digilent Arty A7-100 Master XDC Rev D/E. DDR pins/timing
# are supplied by the unmodified official MIG output products.
set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports CLK100MHZ]
create_clock -name board_clk -period 10.000 [get_ports CLK100MHZ]
set_property -dict {PACKAGE_PIN D9 IOSTANDARD LVCMOS33} [get_ports btn0]
set_property -dict {PACKAGE_PIN A9 IOSTANDARD LVCMOS33} [get_ports uart_txd_in]
set_property -dict {PACKAGE_PIN D10 IOSTANDARD LVCMOS33} [get_ports uart_rxd_out]
set_property -dict {PACKAGE_PIN H5 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
set_property -dict {PACKAGE_PIN J5 IOSTANDARD LVCMOS33} [get_ports {led[1]}]
set_property -dict {PACKAGE_PIN T9 IOSTANDARD LVCMOS33} [get_ports {led[2]}]
set_property -dict {PACKAGE_PIN T10 IOSTANDARD LVCMOS33} [get_ports {led[3]}]
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property DRIVE 8 [get_ports {led[*] uart_rxd_out}]
set_property SLEW SLOW [get_ports {led[*] uart_rxd_out}]
# Asynchronous button and UART input: cut only the first synchronizer stage.
set_false_path -from [get_ports btn0] -to [get_pins -hier -filter {NAME =~ *btn_meta_reg/D || NAME =~ *btn_ref_meta_reg/D}]
set_false_path -from [get_ports uart_txd_in] -to [get_pins -hier -filter {NAME =~ *rx_meta_reg/D}]
# Reset assertion is asynchronous; deassertion is synchronized in each domain.
set_false_path -to [get_pins -hier -filter {NAME =~ *lock_sync_reg*/PRE || NAME =~ *ui_reset_pipe_reg*/PRE}]
# Calibration status crosses ui_clk to core_clk through a two-stage synchronizer.
set_false_path -to [get_pins -hier -regexp {.*calib_sync_reg\[0\]/D}]
# Human-visible indicators and asynchronous serial TX have no external clock.
set_false_path -to [get_ports {led[*] uart_rxd_out}]
# DDR RESET_N is an asynchronous memory reset, sequenced by the unmodified MIG
# initialization FSM. It is not a command/data signal sampled on DDR CK edges.
set_false_path -to [get_ports ddr3_reset_n]
