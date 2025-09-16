// Real-number model ideal ADC: real/wreal in -> logic vector out
module ideal_adc #(
  parameter int BITS = 8,
  parameter real VFS = 1.0
) (
  input real vin,
  output logic [BITS-1:0] code
);
  real vclip;
  int q;
  always @* begin
    vclip = (vin > VFS) ? VFS : ((vin < -VFS) ? -VFS : vin);
    q = int'(((vclip + VFS) / (2.0*VFS)) * (2**BITS - 1) + 0.5);
    if (q < 0) q = 0;
    if (q > (2**BITS - 1)) q = (2**BITS - 1);
    code = logic'(q);
  end
endmodule
