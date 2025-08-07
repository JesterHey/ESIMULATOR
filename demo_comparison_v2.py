#!/usr/bin/env python3
"""
ESIMULATOR 对比演示 - 重组版本
"""

import sys
import os

# 添加新的包路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esimulator'))

from esimulator.core.linearity_analyzer import LinearityAnalyzer

def main():
    """演示主函数"""
    print("DFG线性分析方法对比演示 (重组版)")
    print("=" * 50)
    
    dfg_file = "dfg_files/4004_dfg.txt"
    
    if not os.path.exists(dfg_file):
        print(f"错误: 找不到DFG文件 {dfg_file}")
        return 1
    
    # 执行分析
    analyzer = LinearityAnalyzer()
    try:
        result = analyzer.analyze_dfg_file(dfg_file)
        summary = result['summary']
        
        print("\n=== 修正后的分析结果 (正确) ===")
        print(f"总表达式数: {summary['total_expressions']}")
        print(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})")
        print(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})")
        
        print("\n=== 方法对比 ===")
        print("原始方法 (错误): 63.2% 线性度 (运算符级别统计)")
        print(f"修正方法 (正确): {summary['linearity_ratio']:.1%} 线性度 (表达式级别分析)")
        print(f"修正幅度: {abs(0.632 - summary['linearity_ratio']):.1%}")
        
        print("\n=== 修正要点 ===")
        print("1. 表达式级别分析 vs 运算符级别统计")
        print("2. 一票否决制：任何非线性运算符 → 整个表达式非线性")
        print("3. 位移运算重新分类为非线性 (x << n ≡ x × 2ⁿ)")
        print("4. 条件分支本质非线性")
        
        return 0
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
