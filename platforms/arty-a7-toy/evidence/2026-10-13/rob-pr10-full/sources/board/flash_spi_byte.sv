// Read-only boot software uses this mode-0 byte engine; no Flash writes in RTL.
// 25 MHz / (2 * 4) = 3.125 MHz. Two MISO synchronizers settle within a half bit.
module flash_spi_byte (
  input wire clk, reset, start,
  input wire [7:0] tx_data,
  input wire miso,
  output reg busy, sck,
  output wire mosi,
  output reg [7:0] rx_data
);
  (* ASYNC_REG="TRUE", SHREG_EXTRACT="NO" *) reg miso_meta, miso_sync;
  reg [7:0] shift_tx, shift_rx;
  reg [2:0] bit_count;
  reg [1:0] divider;
  assign mosi=shift_tx[7];
  always @(posedge clk) begin
    miso_meta<=miso;miso_sync<=miso_meta;
    if(reset) begin
      busy<=0;sck<=0;shift_tx<=0;shift_rx<=0;rx_data<=0;bit_count<=0;divider<=0;
    end else if(!busy) begin
      sck<=0;
      if(start) begin busy<=1;shift_tx<=tx_data;shift_rx<=0;bit_count<=0;divider<=0;end
    end else if(divider==3) begin
      divider<=0;sck<=!sck;
      if(!sck) shift_rx<={shift_rx[6:0],miso_sync};
      else begin
        shift_tx<={shift_tx[6:0],1'b1};
        if(bit_count==7) begin busy<=0;rx_data<=shift_rx;end
        else bit_count<=bit_count+1'b1;
      end
    end else divider<=divider+1'b1;
  end
endmodule
