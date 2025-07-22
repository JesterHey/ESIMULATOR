#!/usr/bin/env python3
"""
基于DFG自动生成的alu1模拟器
源文件: /Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/alu1_dfg.txt
"""

def simulate_alu1(a, b, c, op):
    """基于DFG生成的alu1模拟器"""
    # Case 0: (a + b) * c
    _rn0_result = ((a + b) * c)

    # Case 1: (a - b) ^ c
    _rn1_result = ((a - b) ^ c)

    # Case 2: a & (b | c)
    _rn2_result = (a & (b | c))

    # Case 3: (a % b) + (a * c)
    _rn3_result = ((a % b if b != 0 else 0) + (a * c))

    # Default case: 0
    _rn4_result = 0

    # Output selection logic
    result = (_rn0_result if (op == 0b00) else (_rn1_result if (op == 0b01) else (_rn2_result if (op == 0b10) else (_rn3_result if (op == 0b11) else _rn4_result))))

    return result


if __name__ == "__main__":
    import random

    # 预定义测试用例
    test_cases = [
        (5, 3, 2, 0),   # Case 0
        (5, 3, 2, 1),   # Case 1
        (5, 3, 2, 2),   # Case 2
        (5, 3, 2, 3),   # Case 3
        (15, 7, 4, 0),  # More test cases
        (15, 7, 4, 1),
        (15, 7, 4, 2),
        (15, 7, 4, 3),
    ]

    print('=== 预定义测试用例 ===')
    for a, b, c, op in test_cases:
        result = simulate_alu1(a, b, c, op)
        print(f"a={a}, b={b}, c={c}, op={op} => result={result}")

    print('\n=== 随机测试用例 ===')
    for i in range(10):
        a, b, c, op = random.randint(0, 15), random.randint(0, 15), random.randint(0, 15), random.randint(0, 3)
        result = simulate_alu1(a, b, c, op)
        print(f"Test {i+1}: a={a}, b={b}, c={c}, op={op} => result={result}")