# Digilent Arty-A7-100-Master.xdc Rev D/E; CCLK is owned by STARTUPE2.
set_property -dict {PACKAGE_PIN A8 IOSTANDARD LVCMOS33} [get_ports sw0]
set_property -dict {PACKAGE_PIN L13 IOSTANDARD LVCMOS33} [get_ports flash_cs_n]
set_property -dict {PACKAGE_PIN K17 IOSTANDARD LVCMOS33} [get_ports flash_mosi]
set_property -dict {PACKAGE_PIN K18 IOSTANDARD LVCMOS33} [get_ports flash_miso]
set_property -dict {PACKAGE_PIN L14 IOSTANDARD LVCMOS33} [get_ports flash_wp_n]
set_property -dict {PACKAGE_PIN M14 IOSTANDARD LVCMOS33} [get_ports flash_hold_n]
set_property DRIVE 8 [get_ports {flash_cs_n flash_mosi flash_wp_n flash_hold_n}]
set_property SLEW SLOW [get_ports {flash_cs_n flash_mosi flash_wp_n flash_hold_n}]
set_false_path -from [get_ports sw0] -to [get_pins -hier -filter {NAME =~ *sw_meta_reg/D}]
# Serial input sampled after two synchronizer stages. Mode-0 half bit is 160 ns;
# the external data settles before these stages, then is sampled on the next rise.
set_false_path -from [get_ports flash_miso] -to [get_pins -hier -filter {NAME =~ *miso_meta_reg/D}]
set_false_path -to [get_ports {flash_cs_n flash_mosi flash_wp_n flash_hold_n}]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 1 [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 16 [current_design]
set_property BITSTREAM.CONFIG.SPI_FALL_EDGE YES [current_design]
