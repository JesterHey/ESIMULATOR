#!/usr/bin/env python3
"""
基于DFG生成的 alu1 模块模拟器
"""

def simulate_alu1(a, b, c, op):
    """模拟ALU1模块的行为"""
    # op == 2'b00: result = (a + b) * c
    _rn0_result = (a + b) * c
    # op == 2'b01: result = (a - b) ^ c
    _rn1_result = (a - b) ^ c
    # op == 2'b10: result = a & (b | c)
    _rn2_result = a & (b | c)
    # op == 2'b11: result = (a % b) + (a * c)
    _rn3_result = (a % b) + (a * c) if b != 0 else a * c
    # default case
    _rn4_result = 0

    # 根据操作码选择结果
    if op == 0b00:
        result = _rn0_result
    elif op == 0b01:
        result = _rn1_result
    elif op == 0b10:
        result = _rn2_result
    elif op == 0b11:
        result = _rn3_result
    else:
        result = _rn4_result

    # 确保结果在9位范围内
    return result & 0x1FF


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        (5, 3, 2, 0b00),  # (5+3)*2 = 16
        (5, 3, 2, 0b01),  # (5-3)^2 = 2^2 = 0
        (5, 3, 2, 0b10),  # 5&(3|2) = 5&3 = 1
        (5, 3, 2, 0b11),  # (5%3)+(5*2) = 2+10 = 12
        (5, 3, 2, 0b100), # default = 0
    ]

    for a, b, c, op in test_cases:
        result = simulate_alu1(a, b, c, op)
        print(f"a={a}, b={b}, c={c}, op={op:02b} => result={result}")