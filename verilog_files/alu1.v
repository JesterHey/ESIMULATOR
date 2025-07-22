module alu1 (
    input [3:0] a,
    input [3:0] b,
    input [3:0] c,
    input [1:0] op,
    output reg [8:0] result
);
    always @(*) begin
        case (op)
            2'b00: result = (a + b) * c; 
            2'b01: result = (a - b) ^ c; 
            2'b10: result = a & (b | c); 
            2'b11: result = (a % b) + (a * c);
            default: result = 8'b0;
        endcase
    end
endmodule
