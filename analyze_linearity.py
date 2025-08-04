#!/usr/bin/env python3
"""
Intel 4004 ALU DFG线性分析主程序
修正版本 - 按表达式级别分析线性特征
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer

def main():
    """主函数"""
    print("Intel 4004 ALU DFG线性分析工具 (修正版)")
    print("=" * 50)
    
    # 分析DFG文件
    analyzer = CorrectedLinearityAnalyzer()
    dfg_file = "dfg_files/4004_dfg.txt"
    
    if not os.path.exists(dfg_file):
        print(f"错误: 找不到DFG文件 {dfg_file}")
        return 1
    
    try:
        report = analyzer.analyze_dfg_file(dfg_file)
        
        print("\n分析完成！")
        print("详细报告已保存到: results/reports/")
        
        return 0
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
