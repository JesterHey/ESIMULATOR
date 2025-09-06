#!/usr/bin/env python3
"""
示例程序：如何使用线性分析结果转换器与模拟退火算法
完整的工作流程演示：从DFG线性分析结果到模拟退火优化
"""

import sys
import os
import argparse
from typing import Optional

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.analyzers.linearity_to_graph_converter import convert_analysis_to_graph
from src.simulated_annealing import SimulatedAnnealing, AnnealingConfig
import networkx as nx


def linear_aware_cost_function(graph, partition):
    """线性感知的成本函数
    
    这个成本函数考虑了以下因素：
    1. 跨分区边的数量（减少通信开销）
    2. 线性和非线性节点的分离程度（便于优化）
    3. 关键路径的连续性
    """
    cross_edge_penalty = 0
    separation_bonus = 0
    total_edges = max(1, graph.number_of_edges())
    
    # 1. 计算跨分区边的惩罚
    for src, dst in graph.edges():
        if partition.get(src, 0) != partition.get(dst, 0):
            cross_edge_penalty += 1
    
    # 2. 计算线性/非线性分离的奖励
    partition_stats = {0: {'linear': 0, 'nonlinear': 0},
                      1: {'linear': 0, 'nonlinear': 0}}
    
    for node, part in partition.items():
        if node in graph.nodes:
            linearity = graph.nodes[node].get('is_linear', None)
            if linearity is True:
                partition_stats[part]['linear'] += 1
            elif linearity is False:
                partition_stats[part]['nonlinear'] += 1
    
    # 计算每个分区的纯度（单一类型节点的比例）
    for part in [0, 1]:
        total_typed = partition_stats[part]['linear'] + partition_stats[part]['nonlinear']
        if total_typed > 0:
            max_type = max(partition_stats[part]['linear'], partition_stats[part]['nonlinear'])
            purity = max_type / total_typed
            separation_bonus += purity * 0.1  # 奖励系数
    
    # 组合成本：跨边惩罚 - 分离奖励
    normalized_cross_penalty = cross_edge_penalty / total_edges
    return normalized_cross_penalty - separation_bonus


def analyze_partition_quality(graph, partition):
    """分析分区质量"""
    stats = {
        'total_nodes': len(partition),
        'partition_distribution': {0: 0, 1: 0},
        'linearity_distribution': {
            0: {'linear': 0, 'nonlinear': 0, 'unknown': 0},
            1: {'linear': 0, 'nonlinear': 0, 'unknown': 0}
        },
        'cross_edges': 0,
        'total_edges': graph.number_of_edges()
    }
    
    # 统计分区分布和线性属性分布
    for node, part in partition.items():
        stats['partition_distribution'][part] += 1
        
        if node in graph.nodes:
            linearity = graph.nodes[node].get('is_linear', None)
            if linearity is True:
                stats['linearity_distribution'][part]['linear'] += 1
            elif linearity is False:
                stats['linearity_distribution'][part]['nonlinear'] += 1
            else:
                stats['linearity_distribution'][part]['unknown'] += 1
    
    # 计算跨分区边数
    for src, dst in graph.edges():
        if partition.get(src, 0) != partition.get(dst, 0):
            stats['cross_edges'] += 1
    
    # 计算比例
    stats['cross_edge_ratio'] = stats['cross_edges'] / max(1, stats['total_edges'])
    stats['balance_ratio'] = min(stats['partition_distribution'].values()) / max(stats['partition_distribution'].values()) if max(stats['partition_distribution'].values()) > 0 else 0
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="DFG线性分析结果到模拟退火优化完整工作流程")
    parser.add_argument("analysis_file", help="线性分析结果文件路径")
    parser.add_argument("--dfg-file", help="DFG文件路径（可选，会自动推断）")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--iterations", type=int, default=1000, help="最大迭代次数")
    parser.add_argument("--temperature", type=float, default=100.0, help="初始温度")
    parser.add_argument("--runs", type=int, default=3, help="多起点运行次数")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    print("=== DFG线性分析结果到模拟退火优化工作流程 ===\n")
    
    try:
        # 1. 转换分析结果为图
        print("1. 转换线性分析结果为图格式...")
        graph, validation = convert_analysis_to_graph(args.analysis_file, args.dfg_file)
        
        if not validation['is_valid']:
            print("   警告：生成的图存在问题：")
            for issue in validation['issues']:
                print(f"     - {issue}")
        
        stats = validation['statistics']
        print(f"   ✓ 转换成功!")
        print(f"   - 节点数: {stats['total_nodes']}")
        print(f"   - 边数: {stats['total_edges']}")
        print(f"   - 线性节点: {stats['linear_nodes']}")
        print(f"   - 非线性节点: {stats['nonlinear_nodes']}")
        print(f"   - 未知节点: {stats['unknown_nodes']}")
        print(f"   - 连通性: {'是' if stats['is_connected'] else '否'}")
        
        # 2. 配置和运行模拟退火
        print(f"\n2. 配置模拟退火算法...")
        config = AnnealingConfig(
            initial_temperature=args.temperature,
            final_temperature=0.01,
            cooling_rate=0.95,
            iterations_per_temp=50,
            max_iterations=args.iterations,
            use_adaptive_temperature=True,
            multi_start_runs=args.runs,
            allow_nonlinear_optimization=True,
            cluster_operation_weights={
                'flip': 0.25,
                'linear_cluster': 0.35,
                'nonlinear_cluster': 0.25,
                'mixed_cluster': 0.15
            }
        )
        
        sa = SimulatedAnnealing(config)
        sa.set_random_seed(args.seed)
        
        print(f"   ✓ 配置完成")
        print(f"   - 初始温度: {config.initial_temperature}")
        print(f"   - 最大迭代: {config.max_iterations}")
        print(f"   - 多起点运行: {config.multi_start_runs}")
        
        # 3. 执行优化
        print(f"\n3. 执行模拟退火优化...")
        result = sa.optimize_multi_start(graph, linear_aware_cost_function)
        
        print(f"   ✓ 优化完成!")
        print(f"   - 最优成本: {result.best_cost:.6f}")
        print(f"   - 总迭代次数: {result.iteration_count}")
        print(f"   - 收敛原因: {result.convergence_reason}")
        
        # 4. 分析结果
        print(f"\n4. 分析优化结果...")
        analysis = sa.analyze_result(result)
        partition_stats = analyze_partition_quality(graph, result.best_partition)
        
        print(f"   ✓ 分析完成!")
        print(f"   - 成本改进: {analysis['cost_improvement']:.2f}%" if analysis['cost_improvement'] is not None else "   - 成本改进: N/A")
        print(f"   - 跨分区边比例: {partition_stats['cross_edge_ratio']:.4f}")
        print(f"   - 分区平衡度: {partition_stats['balance_ratio']:.4f}")
        
        # 分区分布详情
        print(f"\n   分区分布详情:")
        for part in [0, 1]:
            lin_dist = partition_stats['linearity_distribution'][part]
            total_part = partition_stats['partition_distribution'][part]
            print(f"     分区{part}: 总计{total_part}个节点")
            print(f"       - 线性: {lin_dist['linear']} ({lin_dist['linear']/max(1,total_part)*100:.1f}%)")
            print(f"       - 非线性: {lin_dist['nonlinear']} ({lin_dist['nonlinear']/max(1,total_part)*100:.1f}%)")
            print(f"       - 未知: {lin_dist['unknown']} ({lin_dist['unknown']/max(1,total_part)*100:.1f}%)")
        
        # 5. 保存结果（可选）
        if args.output_dir and os.path.exists(os.path.dirname(args.output_dir)):
            print(f"\n5. 保存结果到 {args.output_dir}...")
            os.makedirs(args.output_dir, exist_ok=True)
            
            # 保存分区结果
            partition_file = os.path.join(args.output_dir, "partition_result.txt")
            with open(partition_file, 'w', encoding='utf-8') as f:
                f.write("# DFG线性分析模拟退火优化结果\n")
                f.write(f"# 成本: {result.best_cost:.6f}\n")
                f.write(f"# 迭代次数: {result.iteration_count}\n")
                f.write(f"# 收敛原因: {result.convergence_reason}\n\n")
                f.write("# 格式: 节点名称 分区号 线性属性 原因\n")
                
                for node, part in sorted(result.best_partition.items()):
                    if node in graph.nodes:
                        node_data = graph.nodes[node]
                        linearity = node_data.get('is_linear', None)
                        reason = node_data.get('reason', '未知')
                        lin_text = '线性' if linearity is True else '非线性' if linearity is False else '未知'
                        f.write(f"{node}\t{part}\t{lin_text}\t{reason}\n")
            
            print(f"   ✓ 分区结果已保存到: {partition_file}")
        
        print(f"\n=== 工作流程完成! ===")
        
        # 如果是详细模式，显示一些示例分区
        if args.verbose:
            print(f"\n详细信息:")
            print(f"  成本历史 (最后10次): {result.cost_history[-10:]}")
            
            print(f"\n  示例线性节点分区:")
            linear_count = 0
            for node, part in result.best_partition.items():
                if node in graph.nodes and graph.nodes[node].get('is_linear') is True:
                    if linear_count < 5:
                        print(f"    {node} -> 分区{part}")
                        linear_count += 1
            
            print(f"\n  示例非线性节点分区:")
            nonlinear_count = 0
            for node, part in result.best_partition.items():
                if node in graph.nodes and graph.nodes[node].get('is_linear') is False:
                    if nonlinear_count < 5:
                        reason = graph.nodes[node].get('reason', '未知')[:30]
                        print(f"    {node} -> 分区{part} ({reason})")
                        nonlinear_count += 1
        
        return True
        
    except Exception as e:
        print(f"\n❌ 工作流程失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # 如果没有命令行参数，使用默认的测试文件
        sys.argv = [
            sys.argv[0],
            "/home/runner/work/ESIMULATOR/ESIMULATOR/results/4004_dfg_linearity_analysis.txt",
            "--verbose",
            "--iterations", "800",
            "--runs", "2"
        ]
    
    success = main()
    sys.exit(0 if success else 1)