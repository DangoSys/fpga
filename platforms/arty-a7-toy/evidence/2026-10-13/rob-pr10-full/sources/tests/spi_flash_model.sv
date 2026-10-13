// Simulation-only standard 03h read / 9fh JEDEC model, no Flash writes.
module spi_flash_model #(parameter BYTES=1024, parameter IMAGE="flash.hex") (
  input wire sck, cs_n, mosi, output reg miso=1
);
  reg [7:0] contents [0:BYTES-1];
  reg [7:0] received;
  integer bit_count=0, state=0, address_bytes=0, address=0, id_index=0;
  reg [7:0] command;
  reg [7:0] response;
  initial begin
    $readmemh(IMAGE,contents);
    if($test$plusargs("bad_header")) contents[0]=contents[0]^1;
    if($test$plusargs("bad_payload")) contents[BYTES-1]=contents[BYTES-1]^1;
  end
  always @(posedge sck or posedge cs_n) begin
    if(cs_n) begin state=0;bit_count=0;address=0;address_bytes=0;id_index=0;received=0;command=0;end
    else begin
      received={received[6:0],mosi};
      if(bit_count==7) begin
        if(state==0) begin
          command=received;
          if(received==8'h03) state=1;
          else if(received==8'h9f) begin state=2;response=8'h01;end
          else state=3;
        end else if(state==1) begin
          address=(address<<8)|received;address_bytes=address_bytes+1;
          if(address_bytes==3) begin state=2;response=contents[0];end
        end else if(state==2) begin
          if(command==8'h9f) begin
            id_index=id_index+1;
            response=id_index==1 ? 8'h20 : id_index==2 ? 8'h18 : 8'hff;
          end else begin
            address=address+1;
            response=(address-32'h400000)<BYTES ? contents[address-32'h400000] : 8'hff;
          end
        end
      end
      bit_count=(bit_count+1)&7;
    end
  end
  always @(negedge sck) miso=cs_n || state!=2 ? 1'b1 : response[7-bit_count];
endmodule
