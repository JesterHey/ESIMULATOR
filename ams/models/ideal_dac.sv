// Real-number model ideal DAC: logic vector in -> real/wreal out
module ideal_dac #(
  parameter int BITS = 8,
  parameter real VFS = 1.0
) (
  input  logic [BITS-1:0] code,
  output real vout
);
  int code_i;
  always @* begin
    code_i = int'(code);
    vout = ((code_i * 1.0) / (2**BITS - 1)) * (2.0*VFS) - VFS;
  end
endmodule
