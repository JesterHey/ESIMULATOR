#!/usr/bin/env python3
"""
ESIMULATOR 基本使用示例
"""

import sys
import os

# 添加包路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from esimulator.core.linearity_analyzer import LinearityAnalyzer
from esimulator.core.dfg_parser import DFGParser
from esimulator.core.report_generator import ReportGenerator

def basic_analysis_example():
    """基本分析示例"""
    print("=== ESIMULATOR 基本分析示例 ===\n")
    
    # 1. 解析DFG文件
    dfg_file = "dfg_files/4004_dfg.txt"
    if not os.path.exists(dfg_file):
        print(f"示例DFG文件未找到: {dfg_file}")
        return
    
    print(f"1. 解析DFG文件: {dfg_file}")
    parser = DFGParser()
    parse_result = parser.parse_file(dfg_file)
    print(f"   找到 {parse_result['total_signals']} 个信号")
    
    # 2. 执行线性分析
    print("\n2. 执行线性分析...")
    analyzer = LinearityAnalyzer()
    analysis_result = analyzer.analyze_dfg_file(dfg_file)
    
    # 3. 生成报告
    print("\n3. 生成分析报告...")
    report_gen = ReportGenerator("examples/output")
    
    # 生成文本报告
    txt_file = report_gen.generate_text_report(analysis_result, "example_analysis.txt")
    print(f"   文本报告: {txt_file}")
    
    # 生成JSON报告
    json_file = report_gen.generate_json_report(analysis_result, "example_analysis.json")
    print(f"   JSON报告: {json_file}")
    
    # 4. 显示分析摘要
    print("\n4. 分析摘要:")
    print(report_gen.generate_summary_report(analysis_result))

def signal_exploration_example():
    """信号探索示例"""
    print("\n=== 信号探索示例 ===\n")
    
    dfg_file = "dfg_files/4004_dfg.txt"
    if not os.path.exists(dfg_file):
        print(f"示例DFG文件未找到: {dfg_file}")
        return
    
    parser = DFGParser()
    parser.parse_file(dfg_file)
    
    # 获取所有信号
    signals = parser.list_signals()
    print(f"总共 {len(signals)} 个信号")
    
    # 查看前几个信号的详细信息
    print("\n前5个信号的详细信息:")
    analyzer = LinearityAnalyzer()
    
    for i, signal in enumerate(signals[:5]):
        expr = parser.get_signal_expression(signal)
        expr_type = parser.get_expression_type(expr)
        
        # 分析这个信号
        analysis = analyzer._analyze_signal_expression(signal, expr)
        linearity = "线性" if analysis['is_linear'] else "非线性"
        
        print(f"\n{i+1}. {signal}")
        print(f"   类型: {expr_type}")
        print(f"   线性特征: {linearity}")
        print(f"   原因: {analysis['reason']}")
        print(f"   表达式: {expr[:60]}...")

def custom_analysis_example():
    """自定义分析示例"""
    print("\n=== 自定义分析示例 ===\n")
    
    # 创建自定义分析器
    analyzer = LinearityAnalyzer()
    
    # 修改线性运算符定义（示例）
    print("1. 自定义运算符分类...")
    original_linear = analyzer.linear_operators.copy()
    
    # 假设我们想将位移运算重新分类为线性（仅作演示）
    analyzer.linear_operators.add('Sll')
    analyzer.linear_operators.add('Srl')
    analyzer.nonlinear_operators.discard('Sll')
    analyzer.nonlinear_operators.discard('Srl')
    
    print(f"   修改后的线性运算符: {analyzer.linear_operators}")
    
    # 分析同一个文件
    dfg_file = "dfg_files/4004_dfg.txt"
    if os.path.exists(dfg_file):
        result = analyzer.analyze_dfg_file(dfg_file)
        summary = result['summary']
        print(f"\n2. 自定义分类下的分析结果:")
        print(f"   线性度: {summary['linearity_ratio']:.1%}")
        print(f"   线性表达式: {summary['linear_expressions']}")
    
    # 恢复原始设置
    analyzer.linear_operators = original_linear
    analyzer.nonlinear_operators.add('Sll')
    analyzer.nonlinear_operators.add('Srl')
    print("\n3. 已恢复原始运算符分类")

if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("examples/output", exist_ok=True)
    
    # 运行示例
    basic_analysis_example()
    signal_exploration_example()
    custom_analysis_example()
    
    print("\n=== 示例运行完成 ===")
    print("查看 examples/output/ 目录获取生成的报告文件")
