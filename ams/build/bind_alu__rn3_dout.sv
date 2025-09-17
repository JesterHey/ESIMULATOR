
// Auto-generated wrapper for bind: alu._rn3_dout
module bind_alu__rn3_dout #(parameter int WIDTH = 8) (
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
