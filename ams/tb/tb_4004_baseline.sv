`timescale 1ns/1ps
module tb_4004_baseline;
  // Clock & reset
  logic sysclk; initial sysclk = 0; always #5 sysclk = ~sysclk; // 100MHz
  logic rst_n;  initial begin rst_n = 0; #50 rst_n = 1; end

  // Deterministic RNG seeding via +seed=<int>
  int seed;
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    void'($urandom(seed));
  end

  // ALU I/O
  logic a12, m12, x12, poc;
  tri   [3:0] data;
  wire  acc_0, add_0, cmram0, cmram1, cmram2, cmram3, cmrom;
  wire  cy_1;

  // Drive control inputs with same stimulus as AMS TB
  initial begin
    a12 = 0; m12 = 0; x12 = 0; poc = 1;
    #100 poc = 0;
    repeat (200) begin
      @(posedge sysclk);
      a12 <= $urandom_range(0,1);
      m12 <= $urandom_range(0,1);
      x12 <= $urandom_range(0,1);
    end
    #200 $finish;
  end

  // Keep data bus tri-stated from TB side
  assign data = 4'bzzzz;

  // DUT only (no bind wrappers)
  alu u_alu (
    .sysclk(sysclk),
    .a12(a12), .m12(m12), .x12(x12), .poc(poc),
    .data(data),
    .acc_0(acc_0), .add_0(add_0), .cy_1(cy_1),
    .cma(1'b0), .write_acc_1(1'b0), .write_carry_2(1'b0), .read_acc_3(1'b0),
    .add_group_4(1'b0), .inc_group_5(1'b0), .sub_group_6(1'b0), .ior(1'b0), .iow(1'b0),
    .ral(1'b0), .rar(1'b0), .ope_n(1'b1), .daa(1'b0), .dcl(1'b0), .inc_isz(1'b0),
    .kbp(1'b0), .o_ib(1'b0), .tcs(1'b0), .xch(1'b0), .n0342(1'b1), .x21_clk2(1'b0),
    .x31_clk2(1'b0), .com_n(1'b1),
    .cmram0(cmram0), .cmram1(cmram1), .cmram2(cmram2), .cmram3(cmram3), .cmrom(cmrom)
  );

  // Simple waveform prints (same format as AMS TB, for diff)
  always @(posedge sysclk) begin
    if (rst_n)
      $display("%t cy_1=%0d add_0=%0d acc_0=%0d cmrom=%0d cmram=%0d%0d%0d%0d",
        $time, cy_1, add_0, acc_0, cmrom, cmram3, cmram2, cmram1, cmram0);
  end
endmodule
