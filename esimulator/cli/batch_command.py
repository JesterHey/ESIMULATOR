#!/usr/bin/env python3
"""
批量分析命令
"""

import os
import sys
from typing import Any

def run_batch(args: Any) -> None:
    """执行批量分析"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    from esimulator.core.report_generator import ReportGenerator
    
    if not os.path.exists(args.input_dir):
        print(f"错误: 找不到输入目录 {args.input_dir}")
        return
    
    # 查找所有DFG文件
    dfg_files = []
    for filename in os.listdir(args.input_dir):
        if filename.endswith('.txt') and 'dfg' in filename.lower():
            dfg_files.append(os.path.join(args.input_dir, filename))
    
    if not dfg_files:
        print(f"在目录 {args.input_dir} 中未找到DFG文件")
        return
    
    print(f"批量分析 {len(dfg_files)} 个DFG文件")
    print("=" * 50)
    
    analyzer = LinearityAnalyzer()
    report_gen = ReportGenerator(args.output)
    
    all_results = {}
    
    for dfg_file in dfg_files:
        filename = os.path.basename(dfg_file)
        print(f"\n正在分析: {filename}")
        
        try:
            result = analyzer.analyze_dfg_file(dfg_file)
            all_results[filename] = result
            
            summary = result['summary']
            print(f"  线性度: {summary['linearity_ratio']:.1%}")
            print(f"  总信号: {summary['total_expressions']}")
            print(f"  线性信号: {summary['linear_expressions']}")
            
            # 生成单独报告
            output_name = f"{os.path.splitext(filename)[0]}_analysis.txt"
            report_gen.generate_text_report(result, output_name)
            
        except Exception as e:
            print(f"  分析失败: {e}")
            continue
    
    # 生成汇总报告
    if all_results:
        generate_batch_summary(all_results, report_gen)
        print(f"\n批量分析完成！结果保存在: {args.output}")

def generate_batch_summary(all_results: dict, report_gen) -> None:
    """生成批量分析汇总报告"""
    summary_file = os.path.join(report_gen.output_dir, "batch_summary.txt")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("批量DFG线性分析汇总报告\n")
        f.write("=" * 40 + "\n\n")
        
        f.write(f"分析文件数: {len(all_results)}\n\n")
        
        f.write("各文件分析结果:\n")
        f.write("-" * 20 + "\n")
        
        total_expressions = 0
        total_linear = 0
        
        for filename, result in all_results.items():
            summary = result['summary']
            total_expressions += summary['total_expressions']
            total_linear += summary['linear_expressions']
            
            f.write(f"{filename:<25}: {summary['linearity_ratio']:>6.1%} "
                   f"({summary['linear_expressions']}/{summary['total_expressions']})\n")
        
        overall_linearity = total_linear / total_expressions if total_expressions > 0 else 0
        f.write(f"\n总体线性度: {overall_linearity:.1%} ({total_linear}/{total_expressions})\n")
    
    print(f"汇总报告已保存到: {summary_file}")
