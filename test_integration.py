#!/usr/bin/env python3
"""
集成测试：测试线性分析结果转换器与模拟退火算法的兼容性
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.analyzers.linearity_to_graph_converter import convert_analysis_to_graph
from src.simulated_annealing import SimulatedAnnealing, AnnealingConfig


def simple_cost_function(graph, partition):
    """简单的成本函数：计算跨分区的边数"""
    cross_edges = 0
    total_edges = 0
    
    for src, dst in graph.edges():
        total_edges += 1
        if partition.get(src, 0) != partition.get(dst, 0):
            cross_edges += 1
    
    # 返回跨分区边的比例
    return cross_edges / max(1, total_edges)


def enhanced_cost_function(graph, partition):
    """增强的成本函数：考虑线性和非线性节点的特性"""
    cross_edges = 0
    total_weighted_edges = 0
    
    for src, dst in graph.edges():
        # 获取节点属性
        src_linear = graph.nodes[src].get('is_linear', None)
        dst_linear = graph.nodes[dst].get('is_linear', None)
        
        # 根据线性属性设置权重
        weight = 1.0
        if src_linear is True and dst_linear is True:
            weight = 0.5  # 线性到线性的边权重较小
        elif src_linear is False or dst_linear is False:
            weight = 2.0  # 涉及非线性节点的边权重较大
        
        total_weighted_edges += weight
        
        if partition.get(src, 0) != partition.get(dst, 0):
            cross_edges += weight
    
    return cross_edges / max(1, total_weighted_edges)


def test_integration():
    """测试集成功能"""
    analysis_file = "/home/runner/work/ESIMULATOR/ESIMULATOR/results/4004_dfg_linearity_analysis.txt"
    
    print("=== 线性分析结果到模拟退火算法集成测试 ===")
    
    try:
        # 1. 转换分析结果为图
        print("\n1. 转换线性分析结果为图...")
        graph, validation = convert_analysis_to_graph(analysis_file)
        
        print(f"   转换成功! 节点数: {graph.number_of_nodes()}, 边数: {graph.number_of_edges()}")
        print(f"   线性节点: {validation['statistics']['linear_nodes']}")
        print(f"   非线性节点: {validation['statistics']['nonlinear_nodes']}")
        
        # 2. 配置模拟退火算法
        print("\n2. 配置模拟退火算法...")
        config = AnnealingConfig(
            initial_temperature=50.0,
            final_temperature=0.01,
            cooling_rate=0.95,
            iterations_per_temp=20,
            max_iterations=500,
            use_adaptive_temperature=True,
            multi_start_runs=2,
            allow_nonlinear_optimization=True
        )
        
        sa = SimulatedAnnealing(config)
        sa.set_random_seed(42)
        
        # 3. 使用简单成本函数进行优化
        print("\n3. 使用简单成本函数进行优化...")
        result_simple = sa.optimize(graph, simple_cost_function)
        
        print(f"   简单成本函数结果:")
        print(f"   - 最优成本: {result_simple.best_cost:.4f}")
        print(f"   - 迭代次数: {result_simple.iteration_count}")
        print(f"   - 收敛原因: {result_simple.convergence_reason}")
        
        # 4. 使用增强成本函数进行优化
        print("\n4. 使用增强成本函数进行优化...")
        result_enhanced = sa.optimize(graph, enhanced_cost_function)
        
        print(f"   增强成本函数结果:")
        print(f"   - 最优成本: {result_enhanced.best_cost:.4f}")
        print(f"   - 迭代次数: {result_enhanced.iteration_count}")
        print(f"   - 收敛原因: {result_enhanced.convergence_reason}")
        
        # 5. 分析分区结果
        print("\n5. 分析分区结果...")
        partition = result_enhanced.best_partition
        
        # 统计分区中的线性和非线性节点分布
        partition_stats = {0: {'linear': 0, 'nonlinear': 0, 'unknown': 0},
                          1: {'linear': 0, 'nonlinear': 0, 'unknown': 0}}
        
        for node, part in partition.items():
            if node in graph.nodes:
                linearity = graph.nodes[node].get('is_linear', None)
                if linearity is True:
                    partition_stats[part]['linear'] += 1
                elif linearity is False:
                    partition_stats[part]['nonlinear'] += 1
                else:
                    partition_stats[part]['unknown'] += 1
        
        print(f"   分区0: 线性={partition_stats[0]['linear']}, "
              f"非线性={partition_stats[0]['nonlinear']}, "
              f"未知={partition_stats[0]['unknown']}")
        print(f"   分区1: 线性={partition_stats[1]['linear']}, "
              f"非线性={partition_stats[1]['nonlinear']}, "
              f"未知={partition_stats[1]['unknown']}")
        
        # 6. 展示一些具体的分区分配
        print(f"\n6. 示例分区分配:")
        linear_examples = []
        nonlinear_examples = []
        
        for node, part in partition.items():
            if node in graph.nodes:
                linearity = graph.nodes[node].get('is_linear', None)
                if linearity is True and len(linear_examples) < 3:
                    linear_examples.append((node, part))
                elif linearity is False and len(nonlinear_examples) < 3:
                    nonlinear_examples.append((node, part))
        
        print("   线性节点示例:")
        for node, part in linear_examples:
            print(f"     {node} -> 分区{part}")
            
        print("   非线性节点示例:")
        for node, part in nonlinear_examples:
            print(f"     {node} -> 分区{part}")
        
        print(f"\n=== 集成测试成功完成! ===")
        return True
        
    except Exception as e:
        print(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)