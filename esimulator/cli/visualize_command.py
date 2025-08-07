#!/usr/bin/env python3
"""
可视化命令
"""

import os
import sys
from typing import Any

def run_visualize(args: Any) -> None:
    """执行可视化生成"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    
    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到DFG文件 {args.dfg_file}")
        return
    
    print(f"正在为DFG文件生成可视化: {args.dfg_file}")
    print("=" * 50)
    
    analyzer = LinearityAnalyzer()
    try:
        result = analyzer.analyze_dfg_file(args.dfg_file)
        
        # 创建输出目录
        os.makedirs(args.output, exist_ok=True)
        
        # 生成可视化（这里先生成文本形式的可视化报告）
        generate_visualization_report(result, args.output)
        
        print(f"可视化结果已保存到: {args.output}")
        
    except Exception as e:
        print(f"可视化过程中出错: {e}")
        sys.exit(1)

def generate_visualization_report(result: dict, output_dir: str) -> None:
    """生成可视化报告"""
    viz_file = os.path.join(output_dir, "visualization_report.txt")
    
    with open(viz_file, 'w', encoding='utf-8') as f:
        f.write("DFG线性分析可视化报告\n")
        f.write("=" * 30 + "\n\n")
        
        summary = result['summary']
        
        # 线性度饼图（文本形式）
        f.write("线性度分布:\n")
        f.write("-" * 15 + "\n")
        linear_ratio = summary['linearity_ratio']
        nonlinear_ratio = 1 - linear_ratio
        
        linear_bar = "█" * int(linear_ratio * 50)
        nonlinear_bar = "█" * int(nonlinear_ratio * 50)
        
        f.write(f"线性    ({linear_ratio:>5.1%}): {linear_bar}\n")
        f.write(f"非线性  ({nonlinear_ratio:>5.1%}): {nonlinear_bar}\n\n")
        
        # 表达式类型分布
        type_dist = result.get('expression_type_distribution', {})
        if type_dist:
            f.write("表达式类型分布:\n")
            f.write("-" * 20 + "\n")
            total = summary['total_expressions']
            
            for expr_type, count in sorted(type_dist.items(), key=lambda x: x[1], reverse=True):
                ratio = count / total
                bar = "█" * int(ratio * 30)
                f.write(f"{expr_type:<12} ({ratio:>5.1%}): {bar} {count}\n")
            f.write("\n")
        
        # 复杂度分布
        complexity_dist = result.get('complexity_distribution', {})
        if complexity_dist:
            f.write("复杂度分布:\n")
            f.write("-" * 15 + "\n")
            
            for complexity, count in sorted(complexity_dist.items(), key=lambda x: x[1], reverse=True):
                ratio = count / total
                bar = "█" * int(ratio * 30)
                f.write(f"{complexity:<10} ({ratio:>5.1%}): {bar} {count}\n")
    
    print(f"可视化报告已保存到: {viz_file}")
    
    # 生成简单的统计图表
    generate_simple_charts(result, output_dir)

def generate_simple_charts(result: dict, output_dir: str) -> None:
    """生成简单的统计图表"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        
        summary = result['summary']
        
        # 线性度饼图
        plt.figure(figsize=(8, 6))
        labels = ['线性', '非线性']
        sizes = [summary['linear_expressions'], summary['nonlinear_expressions']]
        colors = ['#66b3ff', '#ff6666']
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        plt.title('DFG表达式线性度分布')
        plt.savefig(os.path.join(output_dir, 'linearity_distribution.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 表达式类型分布条形图
        type_dist = result.get('expression_type_distribution', {})
        if type_dist:
            plt.figure(figsize=(10, 6))
            types = list(type_dist.keys())
            counts = list(type_dist.values())
            
            plt.bar(types, counts, color='skyblue')
            plt.title('表达式类型分布')
            plt.xlabel('表达式类型')
            plt.ylabel('数量')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'expression_types.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        print("图表已生成: linearity_distribution.png, expression_types.png")
        
    except ImportError:
        print("注意: matplotlib未安装，跳过图表生成")
    except Exception as e:
        print(f"图表生成出错: {e}")
