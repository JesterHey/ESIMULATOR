#!/usr/bin/env python3
"""
DFG线性分析演示脚本
展示修正前后的对比结果
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analyzers.analysis_comparator import compare_analysis_methods

def main():
    """演示主函数"""
    print("DFG线性分析方法对比演示")
    print("=" * 40)
    
    compare_analysis_methods()

if __name__ == "__main__":
    main()
