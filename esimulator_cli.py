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
    linearity_parser.add_argument('--linearity-mode', choices=['arith','gf2'], default='arith', help='线性判定模式 (arith/gf2)')
    linearity_parser.add_argument('--omit-trivial', action='store_true', help='导出时省略无可掩码单元的绑定')
    
    # 对比分析命令
    compare_parser = subparsers.add_parser('compare', help='对比分析方法')
    compare_parser.add_argument('dfg_file', help='DFG文件路径')
    
    # 批量分析命令
    batch_parser = subparsers.add_parser('batch', help='批量分析多个DFG文件')
    batch_parser.add_argument('input_dir', help='包含DFG文件的目录')
    batch_parser.add_argument('--output', '-o', help='输出目录', default='results')
    
    # 可视化命令
    viz_parser = subparsers.add_parser('visualize', help='生成可视化图表 (DOT + HTML)')
    viz_parser.add_argument('dfg_file', help='DFG文件路径')
    viz_parser.add_argument('--output', '-o', help='输出目录', default='results/visualizations')
    viz_parser.add_argument('--filter', choices=['linear','nonlinear'], help='过滤仅显示线性或非线性节点')
    viz_parser.add_argument('--focus', help='以某个信号为根聚焦子图')
    viz_parser.add_argument('--depth', type=int, default=2, help='聚焦子图向前深度 (默认2)')

    # SA 命令（自动导出 + Bind 掩码优化）
    sa_parser = subparsers.add_parser('sa', help='运行 Bind 掩码级模拟退火优化')
    sa_parser.add_argument('dfg_file', help='DFG文件路径')
    sa_parser.add_argument('--output', '-o', help='输出目录', default='results')
    sa_parser.add_argument('--seed', type=int, default=42)
    sa_parser.add_argument('--ti', type=float, default=40.0, help='初始温度')
    sa_parser.add_argument('--tf', type=float, default=0.5, help='终止温度')
    sa_parser.add_argument('--cr', type=float, default=0.92, help='冷却率')
    sa_parser.add_argument('--iters', type=int, default=40, help='每温度迭代次数')
    sa_parser.add_argument('--maxit', type=int, default=2500, help='最大迭代次数')
    sa_parser.add_argument('--runs', type=int, default=3, help='多起点次数')
    # 权重
    sa_parser.add_argument('--wi', type=float, default=0.7)
    sa_parser.add_argument('--wz', type=float, default=1.3)
    sa_parser.add_argument('--w3', type=float, default=0.3)
    sa_parser.add_argument('--wa', type=float, default=1.4)
    sa_parser.add_argument('--area_a1', type=float, default=0.6)
    sa_parser.add_argument('--area_a2', type=float, default=1.2)
    sa_parser.add_argument('--delay_d1', type=float, default=1.2)
    sa_parser.add_argument('--power_p1', type=float, default=0.3)
    sa_parser.add_argument('--iface_i1', type=float, default=0.8)
    # 解析/导出控制
    sa_parser.add_argument('--linearity-mode', choices=['arith','gf2'], default='arith', help='线性判定模式 (arith/gf2)')
    sa_parser.add_argument('--omit-trivial', action='store_true', help='导出时省略无可掩码单元的绑定')
    
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
    elif args.command == 'sa':
        from esimulator.cli.sa_command import run_sa
        run_sa(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
