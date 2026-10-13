# Combine configuration and packed software without crossing partitions.
if {$argc!=3} {error "Usage: make_flash_image.tcl toy_a7.bit flash_payload.bin output.mcs"}
lassign $argv bitfile payload output
set bitfile [file normalize $bitfile]
set payload [file normalize $payload]
set output [file normalize $output]
if {![file isfile $bitfile] || ![file isfile $payload]} {error "Missing input file"}
if {[file size $bitfile]>=0x400000} {error "Configuration exceeds the 4 MiB partition"}
if {[file size $payload]<=32 || [file size $payload]>0xc00000} {error "Invalid software partition size"}
set f [open $payload rb]
set magic [read $f 8]
close $f
if {$magic ne "TOYFLZ4\x00"} {error "Expected a packed TOYFLZ4 image"}
file mkdir [file dirname $output]
write_cfgmem -force -format mcs -interface SPIx1 -size 16 \
  -loadbit [list up 0x00000000 $bitfile] -loaddata [list up 0x00400000 $payload] -file $output
puts "PASS FLASH_IMAGE_LAYOUT: config=0x0 software=0x400000 capacity=16MiB"
exit
