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

# 导出符号列表初始化
__all__ = [
    'CostFunction',
    'get_cost_function',
    'cost_simple_cross',
    'cost_weighted_cross',
    'cost_linear_penalize_nonlinear',
    'cost_mixed'
]

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
               reward_linear_cluster: float = 0.2,
               # 新增: 硬约束与线性上域1偏好
               hard_forbid_nonlinear_domain1: bool = False,
               reward_linear_in_domain1: float = 0.0,
               balance_lambda: float = 0.0,
               non_negative: bool = True) -> float:
    """组合型成本 (可扩展版本):
    组成: cross + penalty + balance - reward
    其中:
      cross  : 跨域边代价 (线性/非线性源加权)
      penalty: 非线性节点放入域1的惩罚
      reward : 线性-线性同域边的奖励 (降低成本)
      balance:  |#domain0 - #domain1| * balance_lambda (域规模不平衡惩罚, 可选)
    若 non_negative=True, 返回 max(0, total)。
    """
    cross = cost_weighted_cross(graph, partition, w_linear=w_cross_linear, w_nonlinear=w_cross_nonlinear)
    penalty = 0.0
    nonlinear_domain1_nodes = 0
    linear_domain1_nodes = 0
    for n, attrs in graph.nodes(data=True):
        is_lin = attrs.get('is_linear', False)
        if not is_lin and partition.get(n, 0) == 1:
            penalty += penalty_nonlinear_domain1
            nonlinear_domain1_nodes += 1
        if is_lin and partition.get(n, 0) == 1:
            linear_domain1_nodes += 1
    # 硬约束: 非线性禁止进入域1
    if hard_forbid_nonlinear_domain1 and nonlinear_domain1_nodes > 0:
        return 1e12  # 大 M 罚值，表示不可行

    reward = 0.0
    for u, v in graph.edges():
        if (graph.nodes[u].get('is_linear') and graph.nodes[v].get('is_linear') and
            partition.get(u) == partition.get(v)):
            reward += reward_linear_cluster
    # 线性节点放在域1的节点级奖励
    if reward_linear_in_domain1 != 0.0 and linear_domain1_nodes > 0:
        reward += reward_linear_in_domain1 * linear_domain1_nodes
    if balance_lambda != 0.0:
        # 二域计数差值
        domain0 = sum(1 for n in partition if partition[n] == 0)
        domain1 = sum(1 for n in partition if partition[n] == 1)
        balance = abs(domain0 - domain1) * balance_lambda
    else:
        balance = 0.0
    total = cross + penalty + balance - reward
    if non_negative and total < 0:
        total = 0.0
    return total

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
    """按名称获取成本函数(柯里化参数), 并为函数附加元数据以便后续分解。
    可选名称: simple_cross, weighted_cross, linear_penalize_nonlinear, mixed
    附加属性:
        _strategy_name: 策略名称
        _strategy_params: 传入参数字典
    """
    if name not in _STRATEGIES:
        raise ValueError(f"未知成本策略: {name}. 可选: {list(_STRATEGIES)}")
    func = _STRATEGIES[name]
    if not kwargs:
        # 直接返回原函数但附加元数据
        setattr(func, '_strategy_name', name)
        setattr(func, '_strategy_params', {})
        return func  # type: ignore
    # 生成带参数闭包
    def _wrapped(graph: nx.DiGraph, partition: Dict[str, int]):
        return func(graph, partition, **kwargs)  # type: ignore
    setattr(_wrapped, '_strategy_name', name)
    setattr(_wrapped, '_strategy_params', kwargs)
    return _wrapped

def decompose_cost(graph: nx.DiGraph, partition: Dict[str, int], strategy_name: str, params: Dict[str, Any]) -> Dict[str, float]:
    """成本分解 (cross/penalty/reward/balance/total/unclamped_total)。
    兼容旧策略, 未涉及项记 0。"""
    cross = penalty = reward = balance = 0.0
    unclamped_total = 0.0
    if strategy_name == 'simple_cross':
        cross = cost_simple_cross(graph, partition)
    elif strategy_name == 'weighted_cross':
        w_linear = params.get('w_linear', 1.0)
        w_nonlinear = params.get('w_nonlinear', 1.0)
        cross = cost_weighted_cross(graph, partition, w_linear=w_linear, w_nonlinear=w_nonlinear)
    elif strategy_name == 'linear_penalize_nonlinear':
        penalty_value = params.get('penalty_nonlinear', 2.0)
        # base cross = simple_cross
        cross = cost_simple_cross(graph, partition)
        for n, attrs in graph.nodes(data=True):
            if not attrs.get('is_linear', False) and partition.get(n, 0) == 1:
                penalty += penalty_value
    elif strategy_name == 'mixed':
        w_cross_linear = params.get('w_cross_linear', 1.0)
        w_cross_nonlinear = params.get('w_cross_nonlinear', 1.5)
        penalty_nonlinear_domain1 = params.get('penalty_nonlinear_domain1', 2.0)
        reward_linear_cluster = params.get('reward_linear_cluster', 0.2)
        hard_forbid_nonlinear_domain1 = params.get('hard_forbid_nonlinear_domain1', False)
        reward_linear_in_domain1 = params.get('reward_linear_in_domain1', 0.0)
        balance_lambda = params.get('balance_lambda', 0.0)
        non_negative = params.get('non_negative', True)
        # 详细诊断统计
        cross_linear_edges = 0
        cross_nonlinear_edges = 0
        for u, v in graph.edges():
            if partition.get(u) != partition.get(v):
                if graph.nodes[u].get('is_linear', False):
                    cross += w_cross_linear
                    cross_linear_edges += 1
                else:
                    cross += w_cross_nonlinear
                    cross_nonlinear_edges += 1
        nonlinear_domain1_nodes = 0
        linear_domain1_nodes = 0
        for n, attrs in graph.nodes(data=True):
            if not attrs.get('is_linear', False) and partition.get(n, 0) == 1:
                penalty += penalty_nonlinear_domain1
                nonlinear_domain1_nodes += 1
            if attrs.get('is_linear', False) and partition.get(n, 0) == 1:
                linear_domain1_nodes += 1
        linear_same_domain_edges = 0
        for u, v in graph.edges():
            if (graph.nodes[u].get('is_linear') and graph.nodes[v].get('is_linear') and
                partition.get(u) == partition.get(v)):
                reward += reward_linear_cluster
                linear_same_domain_edges += 1
        if reward_linear_in_domain1 != 0.0 and linear_domain1_nodes > 0:
            reward += reward_linear_in_domain1 * linear_domain1_nodes
        if balance_lambda != 0.0:
            domain0 = sum(1 for n in partition if partition[n] == 0)
            domain1 = sum(1 for n in partition if partition[n] == 1)
            balance = abs(domain0 - domain1) * balance_lambda
        else:
            domain0 = sum(1 for n in partition if partition[n] == 0)
            domain1 = sum(1 for n in partition if partition[n] == 1)
        # 硬约束处理
        constraint_penalty = 0.0
        if hard_forbid_nonlinear_domain1 and nonlinear_domain1_nodes > 0:
            unclamped_total = 1e12
            total = unclamped_total
            constraint_penalty = unclamped_total
        else:
            unclamped_total = cross + penalty + balance - reward
            total = max(0.0, unclamped_total) if non_negative else unclamped_total
        return {
            'cross': float(cross),
            'penalty': float(penalty),
            'reward': float(reward),
            'balance': float(balance),
            'unclamped_total': float(unclamped_total),
            'total': float(total),
            # 诊断字段
            'cross_linear_edges': float(cross_linear_edges),
            'cross_nonlinear_edges': float(cross_nonlinear_edges),
            'nonlinear_domain1_nodes': float(nonlinear_domain1_nodes),
            'linear_domain1_nodes': float(linear_domain1_nodes),
            'linear_same_domain_edges': float(linear_same_domain_edges),
            'domain0_size': float(domain0),
            'domain1_size': float(domain1),
            'constraint_penalty': float(constraint_penalty)
        }
    # 其它策略
    total = cross + penalty + balance - reward
    return {
        'cross': float(cross),
        'penalty': float(penalty),
        'reward': float(reward),
        'balance': float(balance),
        'unclamped_total': float(total),
        'total': float(total)
    }

__all__.append('decompose_cost')

__all__ = [
    'CostFunction',
    'get_cost_function',
    'cost_simple_cross',
    'cost_weighted_cross',
    'cost_linear_penalize_nonlinear',
    'cost_mixed'
]
