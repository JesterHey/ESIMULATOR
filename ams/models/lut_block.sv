// Simple LUT-based block: maps N-bit input to N-bit output via ROM
module lut_block #(
  parameter int WIDTH = 8,
  parameter int DEPTH = 1 << WIDTH
) (
  input  logic                 clk,
  input  logic                 rst_n,
  input  logic [WIDTH-1:0]     din,
  output logic [WIDTH-1:0]     dout
);
  // A small ROM for mapping; default is identity mapping.
  logic [WIDTH-1:0] rom [0:DEPTH-1];

  // Initialize with identity; users can override via $readmemh or generator
  initial begin : INIT_ROM
    int i;
    for (i = 0; i < DEPTH; i++) begin
      rom[i] = logic'(i[WIDTH-1:0]);
    end
  end

  // Optional: allow runtime override
  // initial $readmemh("lut_init.hex", rom);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      dout <= '0;
    end else begin
      dout <= rom[din];
    end
  end
endmodule
