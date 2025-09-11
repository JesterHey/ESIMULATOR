module demo(
    input c,
    input d,
    output a,
    output b
);
    assign a = b * c - 1;
    assign b = d - 1;
endmodule