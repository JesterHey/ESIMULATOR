#!/usr/bin/env python3
"""
ESIMULATOR 兼容性入口 - 保持原有功能
"""

import sys
import os

# 添加新的包路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esimulator'))

from esimulator.core.linearity_analyzer import LinearityAnalyzer

def main():
    """主函数 - 兼容原有analyze_linearity.py的功能"""
    print("Intel 4004 ALU DFG线性分析工具 (重组版)")
    print("=" * 50)
    
    # 分析DFG文件
    analyzer = LinearityAnalyzer()
    dfg_file = "dfg_files/4004_dfg.txt"
    
    if not os.path.exists(dfg_file):
        print(f"错误: 找不到DFG文件 {dfg_file}")
        return 1
    
    try:
        report = analyzer.analyze_dfg_file(dfg_file)
        
        print("\n分析完成！")
        print("详细报告已保存到: results/")
        
        # 显示摘要
        summary = report['summary']
        print(f"\n分析摘要:")
        print(f"总表达式数: {summary['total_expressions']}")
        print(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})")
        print(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})")
        
        return 0
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
