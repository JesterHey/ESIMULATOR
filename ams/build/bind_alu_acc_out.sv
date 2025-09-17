
// Auto-generated wrapper for bind: alu.acc_out
module bind_alu_acc_out #(parameter int WIDTH = 8) (
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
