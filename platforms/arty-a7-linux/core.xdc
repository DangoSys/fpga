create_clock -name core -period 20.000 [get_ports clock]
set_clock_uncertainty 0.200 [get_clocks core]
set_input_delay 2.000 -clock core [get_ports -filter {DIRECTION == IN && NAME != clock}]
set_output_delay 2.000 -clock core [get_ports -filter {DIRECTION == OUT}]
