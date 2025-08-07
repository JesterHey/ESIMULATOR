#!/usr/bin/env python3
"""
线性分析命令
"""

import os
import sys
from typing import Any

def run_analyze(args: Any) -> None:
    """执行DFG线性分析"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    from esimulator.core.report_generator import ReportGenerator
    
    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到DFG文件 {args.dfg_file}")
        return
    
    print(f"正在分析DFG文件: {args.dfg_file}")
    print("=" * 50)
    
    # 执行分析
    analyzer = LinearityAnalyzer()
    try:
        result = analyzer.analyze_dfg_file(args.dfg_file)
        
        # 生成报告
        report_gen = ReportGenerator(args.output)
        
        if args.format in ['txt', 'both']:
            txt_file = report_gen.generate_text_report(result, "linearity_analysis.txt")
            print(f"文本报告已保存到: {txt_file}")
        
        if args.format in ['json', 'both']:
            json_file = report_gen.generate_json_report(result, "linearity_analysis.json")
            print(f"JSON报告已保存到: {json_file}")
        
        # 打印摘要
        print("\n" + report_gen.generate_summary_report(result))
        
    except Exception as e:
        print(f"分析过程中出错: {e}")
        sys.exit(1)
