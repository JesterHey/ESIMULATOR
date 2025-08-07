#!/usr/bin/env python3
"""
ESIMULATOR 主入口脚本
提供统一的命令行接口
"""

import argparse
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esimulator'))

def main():
    parser = argparse.ArgumentParser(description='ESIMULATOR - DFG线性分析工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 线性分析命令
    linearity_parser = subparsers.add_parser('analyze', help='执行DFG线性分析')
    linearity_parser.add_argument('dfg_file', help='DFG文件路径')
    linearity_parser.add_argument('--output', '-o', help='输出目录', default='results')
    linearity_parser.add_argument('--format', choices=['txt', 'json', 'both'], default='txt', help='输出格式')
    
    # 对比分析命令
    compare_parser = subparsers.add_parser('compare', help='对比分析方法')
    compare_parser.add_argument('dfg_file', help='DFG文件路径')
    
    # 批量分析命令
    batch_parser = subparsers.add_parser('batch', help='批量分析多个DFG文件')
    batch_parser.add_argument('input_dir', help='包含DFG文件的目录')
    batch_parser.add_argument('--output', '-o', help='输出目录', default='results')
    
    # 可视化命令
    viz_parser = subparsers.add_parser('visualize', help='生成可视化图表')
    viz_parser.add_argument('dfg_file', help='DFG文件路径')
    viz_parser.add_argument('--output', '-o', help='输出目录', default='results/visualizations')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        from esimulator.cli.analyze_command import run_analyze
        run_analyze(args)
    elif args.command == 'compare':
        from esimulator.cli.compare_command import run_compare
        run_compare(args)
    elif args.command == 'batch':
        from esimulator.cli.batch_command import run_batch
        run_batch(args)
    elif args.command == 'visualize':
        from esimulator.cli.visualize_command import run_visualize
        run_visualize(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
