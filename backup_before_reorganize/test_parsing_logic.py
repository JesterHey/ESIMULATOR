#!/usr/bin/env python3
"""
测试复杂嵌套表达式的解析逻辑
验证是否存在运算符分类问题
"""

import re
from src.analyzers.correct_linearity_analyzer import CorrectLinearityAnalyzer

def test_complex_expression_parsing():
    """测试复杂表达式的解析"""
    
    # 取一个复杂的嵌套表达式
    complex_expr = "(Operator Unot Next:(Operator And Next:(Operator Or Next:(Terminal alu.x31_clk2),(Operator Unot Next:(Terminal alu.xch))),(Operator Or Next:(Terminal alu.x21_clk2),(Operator Unot Next:(Terminal alu.iow)))))"
    
    print("=== 复杂表达式解析测试 ===")
    print(f"测试表达式: {complex_expr}")
    print()
    
    # 创建分析器实例
    analyzer = CorrectLinearityAnalyzer()
    
    # 手动解析这个表达式
    print("1. 使用正则表达式查找所有运算符:")
    operator_pattern = r'\(Operator (\w+) Next:'
    matches = list(re.finditer(operator_pattern, complex_expr))
    
    for i, match in enumerate(matches):
        operator = match.group(1)
        position = match.start()
        
        # 判断运算类型
        if operator in analyzer.linear_operators:
            op_type = 'linear'
            op_symbol = analyzer.linear_operators[operator]
        elif operator in analyzer.nonlinear_operators:
            op_type = 'nonlinear'
            op_symbol = analyzer.nonlinear_operators[operator]
        else:
            op_type = 'unknown'
            op_symbol = operator
            
        print(f"   运算符 {i+1}: {operator} -> {op_symbol} [{op_type}] (位置: {position})")
    
    print(f"\n2. 实际表达式结构分析:")
    print("   这个表达式的逻辑结构是:")
    print("   ~(A & B) 其中:")
    print("   - A = (x31_clk2 | ~xch)")  
    print("   - B = (x21_clk2 | ~iow)")
    print("   整体是非线性的（因为包含逻辑运算）")
    
    print(f"\n3. 当前算法的处理结果:")
    print("   按出现顺序找到运算符: Unot, And, Or, Unot, Or, Unot")
    print("   全部被分类为非线性运算")
    print("   这个结果是正确的！")
    
    print(f"\n4. 潜在问题分析:")
    test_mixed_expression()

def test_mixed_expression():
    """测试包含线性和非线性运算的混合表达式"""
    
    print("=== 混合表达式测试 ===")
    
    # 构造一个混合表达式：加法 + 逻辑运算
    mixed_expr = "(Operator Plus Next:(Terminal a),(Operator And Next:(Terminal b),(Terminal c)))"
    
    print(f"测试表达式: {mixed_expr}")
    print("逻辑结构: a + (b & c)")
    print("这里有线性运算(+)和非线性运算(&)")
    
    analyzer = CorrectLinearityAnalyzer()
    operator_pattern = r'\(Operator (\w+) Next:'
    matches = list(re.finditer(operator_pattern, mixed_expr))
    
    print("\n找到的运算符:")
    for i, match in enumerate(matches):
        operator = match.group(1)
        if operator in analyzer.linear_operators:
            op_type = 'linear'
        elif operator in analyzer.nonlinear_operators:
            op_type = 'nonlinear'
        else:
            op_type = 'unknown'
        print(f"   {operator} -> {op_type}")
    
    print("\n问题分析:")
    print("1. 当前算法会把每个运算符单独分类")
    print("2. 对于表达式 a + (b & c):")
    print("   - Plus被分类为线性")
    print("   - And被分类为非线性")
    print("3. 但整个表达式的性质取决于最终的合成运算")
    print("4. 实际上 a + (b & c) 整体是非线性的！")
    
    print(f"\n结论:")
    print("当前算法的局限性:")
    print("- 只统计单个运算符，不考虑表达式的整体性质")
    print("- 对于复杂嵌套表达式，无法确定最终的线性/非线性特征")
    print("- 统计结果可能会产生误解")

def analyze_dfg_expression_complexity():
    """分析DFG中实际表达式的复杂度"""
    
    print("\n=== DFG实际表达式复杂度分析 ===")
    
    # 读取DFG文件
    with open("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt", 'r') as f:
        content = f.read()
    
    # 提取所有Bind表达式
    bind_pattern = r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
    matches = list(re.finditer(bind_pattern, content, re.DOTALL))
    
    print(f"总共找到 {len(matches)} 个Bind表达式")
    
    # 分析表达式复杂度
    simple_count = 0  # 只包含一个运算符
    moderate_count = 0  # 包含2-5个运算符
    complex_count = 0  # 包含5个以上运算符
    
    for match in matches:
        dest_signal = match.group(1)
        tree_expr = match.group(2)
        
        # 统计运算符数量
        operator_pattern = r'\(Operator (\w+) Next:'
        operators = re.findall(operator_pattern, tree_expr)
        op_count = len(operators)
        
        if op_count <= 1:
            simple_count += 1
        elif op_count <= 5:
            moderate_count += 1
        else:
            complex_count += 1
            if op_count > 10:  # 显示特别复杂的表达式
                print(f"   复杂表达式 {dest_signal}: {op_count}个运算符")
    
    print(f"\n表达式复杂度分布:")
    print(f"   简单表达式 (≤1个运算符): {simple_count}")
    print(f"   中等表达式 (2-5个运算符): {moderate_count}")
    print(f"   复杂表达式 (>5个运算符): {complex_count}")
    
    print(f"\n建议的改进方向:")
    print("1. 实现表达式树的递归解析")
    print("2. 计算整个表达式的最终线性/非线性特征")
    print("3. 考虑运算符的层次结构和优先级")

if __name__ == "__main__":
    test_complex_expression_parsing()
    test_mixed_expression()
    analyze_dfg_expression_complexity()
