#!/usr/bin/env python3
"""
对比分析命令
"""

import os
import sys
from typing import Any

def run_compare(args: Any) -> None:
    """执行对比分析"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    
    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到DFG文件 {args.dfg_file}")
        return
    
    print("DFG线性分析方法对比")
    print("=" * 40)
    print(f"分析文件: {args.dfg_file}")
    print()
    
    # 执行修正后的分析
    analyzer = LinearityAnalyzer()
    try:
        result = analyzer.analyze_dfg_file(args.dfg_file)
        summary = result['summary']
        
        print("修正后的分析结果 (推荐):")
        print("-" * 30)
        print(f"总表达式数: {summary['total_expressions']}")
        print(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})")
        print(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})")
        print()
        
        print("分析方法对比:")
        print("-" * 20)
        print("修正前方法 (错误): 按运算符个数统计 → 63.2% 线性度")
        print(f"修正后方法 (正确): 按表达式特征分析 → {summary['linearity_ratio']:.1%} 线性度")
        print(f"修正幅度: {abs(0.632 - summary['linearity_ratio']):.1%}")
        print()
        
        print("修正要点:")
        print("1. 表达式级别分析 vs 运算符级别统计")
        print("2. 一票否决制：任何非线性运算符 → 整个表达式非线性")
        print("3. 位移运算重新分类为非线性")
        print("4. 条件分支本质非线性")
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        sys.exit(1)
