module fft_8_pipelined (
    input clk,                     // 系统时钟
    input rst,                     // 复位信号
    // 第一级输入（8个复数，64位宽：32位实部+32位虚部）
    input [31:0] in0_real, in0_imag,
    input [31:0] in1_real, in1_imag,
    input [31:0] in2_real, in2_imag,
    input [31:0] in3_real, in3_imag,
    input [31:0] in4_real, in4_imag,
    input [31:0] in5_real, in5_imag,
    input [31:0] in6_real, in6_imag,
    input [31:0] in7_real, in7_imag,
    // 输出（位反序排列）
    output reg [31:0] out0_real, out0_imag,
    output reg [31:0] out1_real, out1_imag,
    output reg [31:0] out2_real, out2_imag,
    output reg [31:0] out3_real, out3_imag,
    output reg [31:0] out4_real, out4_imag,
    output reg [31:0] out5_real, out5_imag,
    output reg [31:0] out6_real, out6_imag,
    output reg [31:0] out7_real, out7_imag
);

// ---------- 预定义旋转因子（32位定点数，Q1.31格式）----------
// W8^0 = 1.0 + 0.0j
localparam W0_real = 32'h7FFF_FFFF; // ≈1.0
localparam W0_imag = 32'h0000_0000; // 0.0

// W8^2 = 0.0 - 1.0j
localparam W2_real = 32'h0000_0000; // 0.0
localparam W2_imag = 32'h8000_0000; // -1.0

// W8^1 = 0.7071 - 0.7071j (sqrt(2)/2)
localparam W1_real = 32'h5A82_7A99; // ≈0.7071
localparam W1_imag = 32'hA57D_8567; // ≈-0.7071

// W8^3 = -0.7071 - 0.7071j
localparam W3_real = 32'hA57D_8567; // ≈-0.7071
localparam W3_imag = 32'hA57D_8567; // ≈-0.7071

// ---------- 第一级：4个蝶形运算（无乘法）----------
// 组合逻辑计算
wire [31:0] s10_real = in0_real + in4_real;
wire [31:0] s10_imag = in0_imag + in4_imag;
wire [31:0] s14_real = in0_real - in4_real;
wire [31:0] s14_imag = in0_imag - in4_imag;

wire [31:0] s11_real = in1_real + in5_real;
wire [31:0] s11_imag = in1_imag + in5_imag;
wire [31:0] s15_real = in1_real - in5_real;
wire [31:0] s15_imag = in1_imag - in5_imag;

wire [31:0] s12_real = in2_real + in6_real;
wire [31:0] s12_imag = in2_imag + in6_imag;
wire [31:0] s16_real = in2_real - in6_real;
wire [31:0] s16_imag = in2_imag - in6_imag;

wire [31:0] s13_real = in3_real + in7_real;
wire [31:0] s13_imag = in3_imag + in7_imag;
wire [31:0] s17_real = in3_real - in7_real;
wire [31:0] s17_imag = in3_imag - in7_imag;

// 第一级寄存器
reg [31:0] s10_real_reg, s10_imag_reg;
reg [31:0] s11_real_reg, s11_imag_reg;
reg [31:0] s12_real_reg, s12_imag_reg;
reg [31:0] s13_real_reg, s13_imag_reg;
reg [31:0] s14_real_reg, s14_imag_reg;
reg [31:0] s15_real_reg, s15_imag_reg;
reg [31:0] s16_real_reg, s16_imag_reg;
reg [31:0] s17_real_reg, s17_imag_reg;

// 复数乘法辅助函数
function [63:0] complex_mult;
    input [31:0] a_real, a_imag;
    input [31:0] b_real, b_imag;
    begin
        reg [63:0] real_part = $signed(a_real) * $signed(b_real) - $signed(a_imag) * $signed(b_imag);
        reg [63:0] imag_part = $signed(a_real) * $signed(b_imag) + $signed(a_imag) * $signed(b_real);
        // 取高32位（Q1.31定点数）
        complex_mult = {real_part[63:32], imag_part[63:32]};
    end
endfunction

// ---------- 第二级：4个蝶形运算 ----------
// 组合逻辑计算
wire [63:0] bf2_out21, bf2_out23;
assign bf2_out21 = complex_mult(s13_real_reg, s13_imag_reg, W2_real, W2_imag);
wire [31:0] s21_real = s11_real_reg + bf2_out21[63:32];
wire [31:0] s21_imag = s11_imag_reg + bf2_out21[31:0];
wire [31:0] s23_real = s11_real_reg - bf2_out21[63:32];
wire [31:0] s23_imag = s11_imag_reg - bf2_out21[31:0];

wire [63:0] bf2_out25;
assign bf2_out25 = complex_mult(s17_real_reg, s17_imag_reg, W2_real, W2_imag);
wire [31:0] s25_real = s15_real_reg + bf2_out25[63:32];
wire [31:0] s25_imag = s15_imag_reg + bf2_out25[31:0];
wire [31:0] s27_real = s15_real_reg - bf2_out25[63:32];
wire [31:0] s27_imag = s15_imag_reg - bf2_out25[31:0];

// 第二级寄存器
reg [31:0] s20_real_reg, s20_imag_reg;
reg [31:0] s21_real_reg, s21_imag_reg;
reg [31:0] s22_real_reg, s22_imag_reg;
reg [31:0] s23_real_reg, s23_imag_reg;
reg [31:0] s24_real_reg, s24_imag_reg;
reg [31:0] s25_real_reg, s25_imag_reg;
reg [31:0] s26_real_reg, s26_imag_reg;
reg [31:0] s27_real_reg, s27_imag_reg;

// ---------- 第三级：4个蝶形运算 ----------
// 组合逻辑计算
wire [63:0] bf3_out1;
assign bf3_out1 = complex_mult(s21_real_reg, s21_imag_reg, W1_real, W1_imag);
wire [31:0] t1_real = s20_real_reg + bf3_out1[63:32];
wire [31:0] t1_imag = s20_imag_reg + bf3_out1[31:0];
wire [31:0] t5_real = s20_real_reg - bf3_out1[63:32];
wire [31:0] t5_imag = s20_imag_reg - bf3_out1[31:0];

wire [63:0] bf3_out3;
assign bf3_out3 = complex_mult(s23_real_reg, s23_imag_reg, W3_real, W3_imag);
wire [31:0] t3_real = s22_real_reg + bf3_out3[63:32];
wire [31:0] t3_imag = s22_imag_reg + bf3_out3[31:0];
wire [31:0] t7_real = s22_real_reg - bf3_out3[63:32];
wire [31:0] t7_imag = s22_imag_reg - bf3_out3[31:0];

wire [63:0] bf3_out2;
assign bf3_out2 = complex_mult(s25_real_reg, s25_imag_reg, W2_real, W2_imag);
wire [31:0] t2_real = s24_real_reg + bf3_out2[63:32];
wire [31:0] t2_imag = s24_imag_reg + bf3_out2[31:0];
wire [31:0] t6_real = s24_real_reg - bf3_out2[63:32];
wire [31:0] t6_imag = s24_imag_reg - bf3_out2[31:0];

wire [63:0] bf3_out4;
assign bf3_out4 = complex_mult(s27_real_reg, s27_imag_reg, W0_real, W0_imag);
wire [31:0] t4_real = s26_real_reg + bf3_out4[63:32];
wire [31:0] t4_imag = s26_imag_reg + bf3_out4[31:0];
wire [31:0] t0_real = s26_real_reg - bf3_out4[63:32];
wire [31:0] t0_imag = s26_imag_reg - bf3_out4[31:0];

// ---------- 流水线寄存器更新 ----------
always @(posedge clk or posedge rst) begin
    if (rst) begin
        // 复位所有寄存器
        s10_real_reg <= 0; s10_imag_reg <= 0;
        s11_real_reg <= 0; s11_imag_reg <= 0;
        // ... (其他寄存器复位)
        {out0_real, out0_imag} <= 0;
        // ... (其他输出复位)
    end else begin
        // 第一级寄存器
        s10_real_reg <= s10_real; s10_imag_reg <= s10_imag;
        s11_real_reg <= s11_real; s11_imag_reg <= s11_imag;
        s12_real_reg <= s12_real; s12_imag_reg <= s12_imag;
        s13_real_reg <= s13_real; s13_imag_reg <= s13_imag;
        s14_real_reg <= s14_real; s14_imag_reg <= s14_imag;
        s15_real_reg <= s15_real; s15_imag_reg <= s15_imag;
        s16_real_reg <= s16_real; s16_imag_reg <= s16_imag;
        s17_real_reg <= s17_real; s17_imag_reg <= s17_imag;

        // 第二级寄存器
        s20_real_reg <= s10_real_reg + s12_real_reg;
        s20_imag_reg <= s10_imag_reg + s12_imag_reg;
        s21_real_reg <= s21_real; s21_imag_reg <= s21_imag;
        s22_real_reg <= s10_real_reg - s12_real_reg;
        s22_imag_reg <= s10_imag_reg - s12_imag_reg;
        s23_real_reg <= s23_real; s23_imag_reg <= s23_imag;
        s24_real_reg <= s14_real_reg + s16_real_reg;
        s24_imag_reg <= s14_imag_reg + s16_imag_reg;
        s25_real_reg <= s25_real; s25_imag_reg <= s25_imag;
        s26_real_reg <= s14_real_reg - s16_real_reg;
        s26_imag_reg <= s14_imag_reg - s16_imag_reg;
        s27_real_reg <= s27_real; s27_imag_reg <= s27_imag;

        // 第三级输出（位反序排列）
        out0_real <= t0_real; out0_imag <= t0_imag;  // 位反序0->000->0
        out1_real <= t4_real; out1_imag <= t4_imag;  // 位反序4->100->1
        out2_real <= t2_real; out2_imag <= t2_imag;  // 位反序2->010->2
        out3_real <= t6_real; out3_imag <= t6_imag;  // 位反序6->110->3
        out4_real <= t1_real; out4_imag <= t1_imag;  // 位反序1->001->4
        out5_real <= t5_real; out5_imag <= t5_imag;  // 位反序5->101->5
        out6_real <= t3_real; out6_imag <= t3_imag;  // 位反序3->011->6
        out7_real <= t7_real; out7_imag <= t7_imag;  // 位反序7->111->7
    end
end

endmodule