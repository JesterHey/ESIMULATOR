"""
模拟退火算法模块
用于搜索Verilog线性和非线性拆分的最优方案
"""

import numpy as np
import random
import copy
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
import networkx as nx
from pathlib import Path
from partitioning.cost_strategies import get_cost_function, decompose_cost


@dataclass
class AnnealingConfig:
    """模拟退火配置参数"""
    initial_temperature: float = 1000.0
    final_temperature: float = 0.1
    cooling_rate: float = 0.95
    iterations_per_temp: int = 100
    max_iterations: int = 10000
    min_improvement: float = 1e-6
    # 是否启用自适应温度调度
    use_adaptive_temperature: bool = True
    # 多起点次数（>=1 表示多次随机起点）
    multi_start_runs: int = 1
    # 聚类操作权重配置
    cluster_operation_weights: Optional[Dict[str, float]] = None
    # 非线性节点是否允许参与优化（True=允许，False=固定为0）
    allow_nonlinear_optimization: bool = True


@dataclass
class AnnealingResult:
    """模拟退火结果"""
    best_partition: Dict[str, int]
    best_cost: float
    cost_history: List[float]
    temperature_history: List[float]
    iteration_count: int
    convergence_reason: str


class SimulatedAnnealing:
    """模拟退火算法实现"""
    
    def __init__(self, config: Optional[AnnealingConfig] = None):
        self.config = config or AnnealingConfig()
        self.random_seed = None
        
        # 设置默认聚类操作权重
        if self.config.cluster_operation_weights is None:
            self.config.cluster_operation_weights = {
                'flip': 0.3,
                'linear_cluster': 0.3,
                'nonlinear_cluster': 0.2,
                'mixed_cluster': 0.2
            }
    
    def set_random_seed(self, seed: int):
        """设置随机种子"""
        self.random_seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    def optimize(self, 
                graph: nx.DiGraph,
                cost_function: Callable,
                initial_partition: Optional[Dict[str, int]] = None) -> AnnealingResult:
        """执行单次模拟退火优化（支持自适应温度）"""
        
        # 初始化：若未给定初始分区，则按“非线性=0，线性随机”生成
        if initial_partition is None:
            partition = self._generate_linear_random_partition(graph)
        else:
            partition = copy.deepcopy(initial_partition)
        
        current_partition = copy.deepcopy(partition)
        best_partition = copy.deepcopy(partition)
        
        # 计算初始成本
        current_cost_metrics = cost_function(graph, current_partition)
        current_cost = current_cost_metrics.total_cost if hasattr(current_cost_metrics, 'total_cost') else current_cost_metrics
        best_cost = current_cost
        
        # 初始化温度
        temperature = self.config.initial_temperature
        
        # 记录历史
        cost_history = [current_cost]
        temperature_history = [temperature]
        
        iteration = 0
        no_improvement_count = 0
        
        while (temperature > self.config.final_temperature and 
               iteration < self.config.max_iterations):
            
            # 在当前温度下进行多次迭代
            for _ in range(self.config.iterations_per_temp):
                # 生成新解（仅在线性可变节点上操作）
                new_partition = self._generate_neighbor_linear_only(current_partition, graph)
                
                # 计算新成本
                new_cost_metrics = cost_function(graph, new_partition)
                new_cost = new_cost_metrics.total_cost if hasattr(new_cost_metrics, 'total_cost') else new_cost_metrics
                
                # 计算成本差
                delta_cost = new_cost - current_cost
                
                # 接受准则
                if delta_cost < 0 or self._accept_probability(delta_cost, temperature):
                    current_partition = copy.deepcopy(new_partition)
                    current_cost = new_cost
                    
                    # 更新最优解
                    if new_cost < best_cost:
                        best_partition = copy.deepcopy(new_partition)
                        best_cost = new_cost
                        no_improvement_count = 0
                    else:
                        no_improvement_count += 1
                else:
                    no_improvement_count += 1
                
                iteration += 1
                
                # 记录历史
                cost_history.append(current_cost)
                temperature_history.append(temperature)
                
                # 检查收敛条件
                if no_improvement_count > 1000:  # 连续1000次无改进
                    break
            
            # 更新温度：可选自适应或固定冷却
            if self.config.use_adaptive_temperature:
                temperature = self.adaptive_temperature_schedule(iteration, best_cost, cost_history)
            else:
                temperature *= self.config.cooling_rate
            
            # 检查收敛
            if len(cost_history) > 100:
                recent_costs = cost_history[-100:]
                if max(recent_costs) - min(recent_costs) < self.config.min_improvement:
                    break
        
        # 确定收敛原因
        if temperature <= self.config.final_temperature:
            convergence_reason = "温度达到终止条件"
        elif iteration >= self.config.max_iterations:
            convergence_reason = "达到最大迭代次数"
        elif no_improvement_count > 1000:
            convergence_reason = "连续无改进次数过多"
        else:
            convergence_reason = "成本变化小于阈值"
        
        return AnnealingResult(
            best_partition=best_partition,
            best_cost=best_cost,
            cost_history=cost_history,
            temperature_history=temperature_history,
            iteration_count=iteration,
            convergence_reason=convergence_reason
        )
    
    def optimize_multi_start(self,
                             graph: nx.DiGraph,
                             cost_function: Callable,
                             num_starts: Optional[int] = None) -> AnnealingResult:
        """多起点策略：多次随机初始解运行，返回最优结果"""
        runs = num_starts or max(1, self.config.multi_start_runs)
        best_overall: Optional[AnnealingResult] = None
        base_seed = self.random_seed if self.random_seed is not None else random.randint(0, 10**9)

        for i in range(runs):
            # 变化种子以增加多样性
            self.set_random_seed(base_seed + i)
            result = self.optimize(graph, cost_function, initial_partition=None)
            if best_overall is None or result.best_cost < best_overall.best_cost:
                best_overall = result

        if best_overall is None:
            # 理论上不会发生；保险返回一次 optimize 的结果
            best_overall = self.optimize(graph, cost_function, initial_partition=None)
        return best_overall

    # ---------------- 结果导出 / 分解 ----------------
    def export_best_partition(self, result: AnnealingResult, path: str, graph: nx.DiGraph, cost_function: Callable):
        """导出最优分区 JSON，包含成本分解 (cross/penalty/reward/total)。
        当成本策略不支持分解字段时，缺失部分为0。"""
        strategy_name = getattr(cost_function, '_strategy_name', 'unknown')
        strategy_params = getattr(cost_function, '_strategy_params', {})
        breakdown = {}
        try:
            breakdown = decompose_cost(graph, result.best_partition, strategy_name, strategy_params)
        except Exception:
            breakdown = {
                'cross': None,
                'penalty': None,
                'reward': None,
                'total': result.best_cost
            }
        payload = {
            'strategy': strategy_name,
            'strategy_params': strategy_params,
            'best_cost': result.best_cost,
            'convergence_reason': result.convergence_reason,
            'iteration_count': result.iteration_count,
            'partition': result.best_partition,
            'cost_breakdown': breakdown
        }
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        import json
        path_obj.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        return str(path_obj)
    
    def _generate_linear_random_partition(self, graph: nx.DiGraph) -> Dict[str, int]:
        """初始化分区：根据配置决定非线性节点的分配策略"""
        partition: Dict[str, int] = {}
        for node in graph.nodes():
            node_attr = graph.nodes[node]
            is_linear = bool(node_attr.get('is_linear', False))
            if is_linear:
                partition[node] = random.randint(0, 1)
            else:
                # 如果允许非线性节点优化，则随机分配；否则固定为0
                if self.config.allow_nonlinear_optimization:
                    partition[node] = random.randint(0, 1)
                else:
                    partition[node] = 0  # 非线性强制在电子域
        return partition
    
    def _get_linear_nodes(self, graph: nx.DiGraph) -> List[str]:
        """获取线性可变节点列表"""
        linear_nodes: List[str] = []
        for node in graph.nodes():
            if bool(graph.nodes[node].get('is_linear', False)):
                linear_nodes.append(node)
        return linear_nodes
    
    def _generate_neighbor_linear_only(self, partition: Dict[str, int], graph: nx.DiGraph) -> Dict[str, int]:
        """生成邻域解：支持线性和非线性节点的灵活聚类操作"""
        new_partition = copy.deepcopy(partition)
        linear_nodes = self._get_linear_nodes(graph)
        nonlinear_nodes = [n for n in graph.nodes() if not bool(graph.nodes[n].get('is_linear', False))]
        
        if not linear_nodes and not nonlinear_nodes:
            return new_partition
        
        # 根据权重随机选择邻域操作类型
        if not self.config.cluster_operation_weights:
            self.config.cluster_operation_weights = {
                'flip': 0.4,
                'linear_cluster': 0.3,
                'nonlinear_cluster': 0.15,
                'mixed_cluster': 0.15
            }
        operations = list(self.config.cluster_operation_weights.keys())
        weights = list(self.config.cluster_operation_weights.values())
        operation = random.choices(operations, weights=weights, k=1)[0]
        
        if operation == 'flip':
            # 随机选择一个节点进行翻转（线性节点优先）
            if linear_nodes and random.random() < 0.7:
                node = random.choice(linear_nodes)
                new_partition[node] = 1 - new_partition[node]
            elif nonlinear_nodes and self.config.allow_nonlinear_optimization:
                node = random.choice(nonlinear_nodes)
                new_partition[node] = 1 - new_partition[node]
                
        elif operation == 'linear_cluster':
            # 线性节点聚类：线性节点朝着线性邻居方向聚合
            if linear_nodes:
                center_node = random.choice(linear_nodes)
                neighbors = [n for n in graph.neighbors(center_node) if n in linear_nodes]
                if neighbors:
                    num_neighbors = random.randint(1, min(3, len(neighbors)))
                    selected = random.sample(neighbors, num_neighbors)
                    target = new_partition[center_node]
                    if random.random() < 0.2:  # 小概率反向以扩大搜索
                        target = 1 - target
                    for n in selected:
                        new_partition[n] = target
                        
        elif operation == 'nonlinear_cluster':
            # 非线性节点聚类：非线性节点可以朝着线性或非线性邻居方向聚合
            if nonlinear_nodes and self.config.allow_nonlinear_optimization:
                center_node = random.choice(nonlinear_nodes)
                # 获取所有邻居（包括线性和非线性）
                all_neighbors = list(graph.neighbors(center_node))
                if all_neighbors:
                    num_neighbors = random.randint(1, min(3, len(all_neighbors)))
                    selected = random.sample(all_neighbors, num_neighbors)
                    # 选择目标方向：可以是当前分配或邻居的多数分配
                    neighbor_assignments = [new_partition[n] for n in selected]
                    if len(neighbor_assignments) > 0:
                        target = max(set(neighbor_assignments), key=neighbor_assignments.count)
                        if random.random() < 0.3:  # 30%概率反向
                            target = 1 - target
                        for n in selected:
                            new_partition[n] = target
                            
        elif operation == 'mixed_cluster':
            # 混合聚类：允许跨类型的节点聚合
            all_nodes = list(graph.nodes())
            if all_nodes:
                center_node = random.choice(all_nodes)
                all_neighbors = list(graph.neighbors(center_node))
                if all_neighbors:
                    num_neighbors = random.randint(1, min(4, len(all_neighbors)))
                    selected = random.sample(all_neighbors, num_neighbors)
                    target = new_partition[center_node]
                    if random.random() < 0.25:  # 25%概率反向
                        target = 1 - target
                    for n in selected:
                        # 如果非线性节点优化被禁用，则跳过非线性节点
                        if (not self.config.allow_nonlinear_optimization and 
                            not bool(graph.nodes[n].get('is_linear', False))):
                            continue
                        new_partition[n] = target
        
        return new_partition
    
    def _accept_probability(self, delta_cost: float, temperature: float) -> bool:
        """计算接受概率"""
        if temperature <= 0:
            return False
        
        # Metropolis准则
        if delta_cost > 0:
            probability = np.exp(-delta_cost / temperature)
            return random.random() < probability
        else:
            return True
    
    def adaptive_temperature_schedule(self, iteration: int, best_cost: float, 
                                    cost_history: List[float]) -> float:
        """自适应温度调度：根据近期成本波动动态调整温度"""
        if len(cost_history) < 10:
            return self.config.initial_temperature
        
        recent_costs = cost_history[-10:]
        cost_variance = np.var(recent_costs)
        
        # 成本变化大时提高温度，变化小时降低温度
        if cost_variance > 0.05:
            temperature_factor = 1.25
        elif cost_variance < 0.005:
            temperature_factor = 0.75
        else:
            temperature_factor = 1.0
        
        base_temperature = self.config.initial_temperature * (self.config.cooling_rate ** max(1, iteration // self.config.iterations_per_temp))
        return max(self.config.final_temperature, base_temperature * temperature_factor)
    
    def analyze_result(self, result: AnnealingResult) -> Dict[str, Any]:
        """分析优化结果"""
        analysis = {
            'convergence_reason': result.convergence_reason,
            'total_iterations': result.iteration_count,
            'final_cost': result.best_cost,
            'cost_improvement': None,
            'temperature_profile': None,
            'convergence_speed': None
        }
        
        # 计算成本改进: 基于 best_cost 而非最后一步 (避免末尾反弹误差)
        if len(result.cost_history) > 0:
            initial_cost = result.cost_history[0]
            if initial_cost != 0:
                analysis['cost_improvement'] = (initial_cost - result.best_cost) / initial_cost * 100
            else:
                analysis['cost_improvement'] = 0.0
        
        # 分析温度曲线
        if len(result.temperature_history) > 1:
            analysis['temperature_profile'] = {
                'initial_temp': result.temperature_history[0],
                'final_temp': result.temperature_history[-1],
                'cooling_steps': len(result.temperature_history)
            }
        
        # 分析收敛速度
        if len(result.cost_history) > 10:
            early_costs = result.cost_history[:10]
            late_costs = result.cost_history[-10:]
            early_avg = np.mean(early_costs)
            late_avg = np.mean(late_costs)
            analysis['convergence_speed'] = (early_avg - late_avg) / max(1, len(result.cost_history))
        
        return analysis
    
    
if __name__ == "__main__":
    # 仅运行真实图的优化流程；需先通过线性分析生成 results/4004_dfg_linearity_graph.json
    graph_json = Path('results/4004_dfg_linearity_graph.json')
    if not graph_json.exists():
        print('缺少真实图 JSON: results/4004_dfg_linearity_graph.json，请先运行线性分析生成该文件。')
    else:
        from analyzers.graph_loader import load_graph_from_json
        g = load_graph_from_json(str(graph_json))
        # 混合策略 + 域平衡 + 非负截断
        # 约束: 非线性只能在电子域(domain0); 鼓励线性尽量放到 ONN 域(domain1)
        cost_fn = get_cost_function(
            'mixed',
            w_cross_linear=1.0,
            w_cross_nonlinear=1.5,
            penalty_nonlinear_domain1=2.0,
            reward_linear_cluster=0.1,
            hard_forbid_nonlinear_domain1=True,
            reward_linear_in_domain1=0.05,
            balance_lambda=0.05,
            non_negative=True,
        )
        # 禁用非线性节点优化，确保它们固定在电子域(0)，与硬约束一致
        cfg = AnnealingConfig(
            iterations_per_temp=40,
            max_iterations=2500,
            multi_start_runs=3,
            allow_nonlinear_optimization=False,
        )
        sa = SimulatedAnnealing(cfg)
        res = sa.optimize_multi_start(g, cost_fn)
        export_path = sa.export_best_partition(res, 'results/4004_best_partition.json', g, cost_fn)
        analysis = sa.analyze_result(res)
        print(
            '[REAL GRAPH] best_cost=',
            res.best_cost,
            'improve=%.2f%%' % (analysis['cost_improvement'] or 0.0),
            'export =>',
            export_path,
        )