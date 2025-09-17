
// Auto-generated wrapper for bind: alu.n0378
module bind_alu_n0378 #(parameter int WIDTH = 8) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic [WIDTH-1:0]  din,
  output logic [WIDTH-1:0]  dout
);
  // Pure-digital LUT backend for traditional simulators
  lut_block #(.WIDTH(WIDTH)) u_lut (
    .clk (clk),
    .rst_n (rst_n),
    .din (din),
    .dout(dout)
  );
endmodule
