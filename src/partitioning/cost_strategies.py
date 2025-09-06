"""分区成本策略模块

提供多种可插拔的成本计算策略，用于模拟退火或其他优化算法。

设计目标:
- 简单跨分区边成本
- 加权(线性/非线性)跨域成本
- 带非线性节点域惩罚
- 组合策略(可叠加)

使用方式:
from partitioning.cost_strategies import get_cost_function
cost_fn = get_cost_function("linear_penalize_nonlinear", penalty_nonlinear=2.0)
value = cost_fn(graph, partition)

partition: Dict[node_name, int]  0/1 表示两个域
节点属性要求:
  is_linear: bool  (由前置分析注入)
"""
from __future__ import annotations
from typing import Dict, Callable, Iterable, Tuple, Any
import networkx as nx

CostFunction = Callable[[nx.DiGraph, Dict[str, int]], float]

# ----------------------------------------------------------------------------
# 基础工具
# ----------------------------------------------------------------------------

def _iter_cross_edges(graph: nx.DiGraph, partition: Dict[str, int]):
    for u, v in graph.edges():
        if partition.get(u) != partition.get(v):
            yield (u, v)

# ----------------------------------------------------------------------------
# 策略实现
# ----------------------------------------------------------------------------

def cost_simple_cross(graph: nx.DiGraph, partition: Dict[str, int]) -> float:
    """最简单: 跨分区边计数"""
    return sum(1 for _ in _iter_cross_edges(graph, partition))

def cost_weighted_cross(graph: nx.DiGraph, partition: Dict[str, int], w_linear: float = 1.0, w_nonlinear: float = 1.0) -> float:
    """根据源节点线性属性加权跨分区边.
    参数:
        w_linear: 源为线性节点时的边权
        w_nonlinear: 源为非线性节点时的边权
    """
    total = 0.0
    for u, v in _iter_cross_edges(graph, partition):
        is_lin = bool(graph.nodes[u].get('is_linear', False))
        total += w_linear if is_lin else w_nonlinear
    return total

def cost_linear_penalize_nonlinear(graph: nx.DiGraph, partition: Dict[str, int], penalty_nonlinear: float = 2.0) -> float:
    """跨分区边 + 非线性节点放入 domain=1 的惩罚."""
    base = cost_simple_cross(graph, partition)
    penalty = 0.0
    for n, attrs in graph.nodes(data=True):
        if not attrs.get('is_linear', False) and partition.get(n, 0) == 1:
            penalty += penalty_nonlinear
    return base + penalty

def cost_mixed(graph: nx.DiGraph, partition: Dict[str, int], *,
               w_cross_linear: float = 1.0,
               w_cross_nonlinear: float = 1.5,
               penalty_nonlinear_domain1: float = 2.0,
               reward_linear_cluster: float = 0.2) -> float:
    """组合型成本:
    - 线性/非线性跨域不同权重
    - 非线性在域1惩罚
    - 奖励线性连续链保持同域 (减少成本)
    """
    cross = cost_weighted_cross(graph, partition, w_linear=w_cross_linear, w_nonlinear=w_cross_nonlinear)
    penalty = 0.0
    for n, attrs in graph.nodes(data=True):
        if not attrs.get('is_linear', False) and partition.get(n, 0) == 1:
            penalty += penalty_nonlinear_domain1
    # 线性链奖励: 对每条 u->v 边, 若两端线性且同域, 减少少量成本
    reward = 0.0
    for u, v in graph.edges():
        if (graph.nodes[u].get('is_linear') and graph.nodes[v].get('is_linear') and
            partition.get(u) == partition.get(v)):
            reward += reward_linear_cluster
    return cross + penalty - reward

# ----------------------------------------------------------------------------
# 选择器
# ----------------------------------------------------------------------------

_STRATEGIES = {
    'simple_cross': cost_simple_cross,
    'weighted_cross': cost_weighted_cross,
    'linear_penalize_nonlinear': cost_linear_penalize_nonlinear,
    'mixed': cost_mixed,
}


def get_cost_function(name: str, **kwargs) -> CostFunction:
    """按名称获取成本函数(柯里化参数).
    可选名称: simple_cross, weighted_cross, linear_penalize_nonlinear, mixed
    """
    if name not in _STRATEGIES:
        raise ValueError(f"未知成本策略: {name}. 可选: {list(_STRATEGIES)}")
    func = _STRATEGIES[name]
    if not kwargs:
        return func  # type: ignore
    # 生成带参数闭包
    def _wrapped(graph: nx.DiGraph, partition: Dict[str, int]):
        return func(graph, partition, **kwargs)  # type: ignore
    return _wrapped

__all__ = [
    'CostFunction',
    'get_cost_function',
    'cost_simple_cross',
    'cost_weighted_cross',
    'cost_linear_penalize_nonlinear',
    'cost_mixed'
]
