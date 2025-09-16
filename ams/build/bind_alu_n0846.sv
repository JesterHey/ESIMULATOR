
// Auto-generated wrapper for bind: alu.n0846
module bind_alu_n0846 #(parameter int WIDTH = 8) (
  input  logic              clk,
  input  logic              rst_n,
  // 数字输入/输出（占位）：可按需求拆分为多个输入向量
  input  logic [WIDTH-1:0]  din,
  output logic [WIDTH-1:0]  dout
);
  // 占位：ADC/DAC 可根据真实上下文放置在更外层或内部；此处仅示例链路
  // 数字->实值->ONN->数字
  real r_in;
  ideal_dac #(.BITS(WIDTH), .VFS(1.0)) u_dac (
    .code (din),
    .vout (r_in)
  );

  logic [WIDTH-1:0] onn_out;
  onn_linear_block #(
    .PARAM_INPUTS (1),
    .PARAM_OUTPUTS(1),
    .PARAM_WIDTH  (WIDTH),
    .SCALE_W      (1.0)
  ) u_onn (
    .din_flat  (din),
    .dout_flat (onn_out)
  );

  // 实值->数字（此处将 ONN 数字直接输出；若 ONN 输出为 real，可改为 ideal_adc）
  assign dout = onn_out;
endmodule
