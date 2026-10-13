# Arty A7-100T volatile JTAG entry point, usable from any working directory.
# vivado -mode batch -source /path/to/program.tcl -tclargs /path/to/toy_a7.bit
# Delegates to the exact board script used by the recorded hardware run.
set toy_program_script [file join [file dirname [file normalize [info script]]] board program_arty.tcl]
source $toy_program_script
