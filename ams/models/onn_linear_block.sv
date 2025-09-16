// ONN linear block (RNM placeholder): maps N digital inputs to M digital outputs
// Internally uses real-valued accumulation with fixed-point scaling.
module onn_linear_block #(
  parameter int PARAM_INPUTS  = 4,
  parameter int PARAM_OUTPUTS = 4,
  parameter int PARAM_WIDTH   = 8,  // bits per input/output
  parameter real SCALE_W      = 1.0 // weight scale
) (
  input  logic [PARAM_INPUTS*PARAM_WIDTH-1:0]  din_flat,
  output logic [PARAM_OUTPUTS*PARAM_WIDTH-1:0] dout_flat
);
  // Unpack inputs to integer array
  int din   [0:PARAM_INPUTS-1];
  int douti [0:PARAM_OUTPUTS-1];
  real rin  [0:PARAM_INPUTS-1];
  real rout [0:PARAM_OUTPUTS-1];

  // Simple deterministic weights placeholder (can be replaced by generator)
  function real weight_of(int o, int i);
    weight_of = SCALE_W * ((o+1)*(i+1) % 3 - 1); // {-1,0,1} scaled
  endfunction

  // Unpack flat input bus
  genvar gi;
  generate
    for (gi = 0; gi < PARAM_INPUTS; gi++) begin : UNPACK
      always @* begin
        din[gi] = int'(din_flat[(gi+1)*PARAM_WIDTH-1 -: PARAM_WIDTH]);
        rin[gi] = (din[gi] * 1.0) / (2**PARAM_WIDTH - 1) * 2.0 - 1.0; // map to [-1,1]
      end
    end
  endgenerate

  // Compute outputs (real accumulation -> quantize to logic)
  integer oi, ii;
  always @* begin
    for (oi = 0; oi < PARAM_OUTPUTS; oi++) begin
      real acc;
      acc = 0.0;
      for (ii = 0; ii < PARAM_INPUTS; ii++) begin
        acc += rin[ii] * weight_of(oi, ii);
      end
      // map back to [0, 2^WIDTH-1]
      real y = (acc + 1.0) * 0.5;
      if (y < 0.0) y = 0.0;
      if (y > 1.0) y = 1.0;
      douti[oi] = int'(y * (2**PARAM_WIDTH - 1) + 0.5);
    end
  end

  // Pack outputs
  generate
    for (gi = 0; gi < PARAM_OUTPUTS; gi++) begin : PACK
      always @* begin
        dout_flat[(gi+1)*PARAM_WIDTH-1 -: PARAM_WIDTH] = logic'(douti[gi]);
      end
    end
  endgenerate
endmodule
