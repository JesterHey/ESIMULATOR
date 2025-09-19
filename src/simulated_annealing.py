"""
模拟退火算法模块
用于搜索Verilog线性和非线性拆分的最优方案
"""

import math
try:
    import numpy as np  # 优先使用 numpy
except Exception:
    # 轻量级兼容层：当 numpy 不可用时，提供最小所需 API
    class _NP:
        @staticmethod
        def exp(x):
            return math.exp(x)
        @staticmethod
        def var(arr):
            if not arr:
                return 0.0
            m = sum(arr) / len(arr)
            return sum((x - m) ** 2 for x in arr) / len(arr)
        @staticmethod
        def mean(arr):
            if not arr:
                return 0.0
            return sum(arr) / len(arr)
        class random:  # noqa: N801
            @staticmethod
            def seed(seed):
                import random as _r
                _r.seed(seed)
    np = _NP()
import random
import copy
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
try:
    import networkx as nx
except Exception:
    nx = None  # type: ignore
from pathlib import Path
# cost_strategies 仅在图级优化中用到，这里不做顶层导入以避免 networkx 依赖
import json


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
            try:
                np.random.seed(seed)  # 若为兼容层，则退化为 random.seed
            except Exception:
                pass
    
    def optimize(self, 
                graph: Any,
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
                             graph: Any,
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
    def export_best_partition(self, result: AnnealingResult, path: str, graph: Any, cost_function: Callable):
        """导出最优分区 JSON，包含成本分解 (cross/penalty/reward/total)。
        当成本策略不支持分解字段时，缺失部分为0。"""
        strategy_name = getattr(cost_function, '_strategy_name', 'unknown')
        strategy_params = getattr(cost_function, '_strategy_params', {})
        breakdown = {}
        try:
            from partitioning.cost_strategies import decompose_cost  # 局部导入
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
    
    def _generate_linear_random_partition(self, graph: Any) -> Dict[str, int]:
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
    
    def _get_linear_nodes(self, graph: Any) -> List[str]:
        """获取线性可变节点列表"""
        linear_nodes: List[str] = []
        for node in graph.nodes():
            if bool(graph.nodes[node].get('is_linear', False)):
                linear_nodes.append(node)
        return linear_nodes
    
    def _generate_neighbor_linear_only(self, partition: Dict[str, int], graph: Any) -> Dict[str, int]:
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
    

# ---------------- Bind 掩码级 SA：类型与工具（供外部导入） ----------------

@dataclass
class BindCostWeights:
    wi: float = 1.0
    wz: float = 1.0
    w3: float = 1.0
    wa: float = 1.0
    area_a1: float = 1.0
    area_a2: float = 0.5
    delay_d1: float = 1.0
    power_p1: float = 0.5
    iface_i1: float = 0.2


class BindMaskProblem:
    def __init__(self, bind_json_path: str):
        self.path = bind_json_path
        payload = json.loads(Path(bind_json_path).read_text(encoding='utf-8'))
        self.binds = payload.get('binds', [])
        self.per_bind = []
        for b in self.binds:
            order = b.get('workset_order') or b.get('operator_order', [])
            mask = b.get('workset_mask') or b.get('operator_mask', [])
            fadj = b.get('fusable_adj', [])
            op_count = b.get('operator_count', len(order))
            id_to_idx = {op_id: idx for idx, op_id in enumerate(order)}
            allowed = {i for i, bit in enumerate(mask) if bit == 1}
            edges_idx = []
            for a, c in fadj:
                if a in id_to_idx and c in id_to_idx:
                    edges_idx.append((id_to_idx[a], id_to_idx[c]))
            self.per_bind.append({
                'dest': b.get('dest'),
                'order': order,
                'orig_mask': mask,
                'mask_len': op_count,
                'allowed': allowed,
                'edges': edges_idx,
                'sources': b.get('sources', []),
            })

    def initial_state(self):
        state = []
        for pb in self.per_bind:
            state.append(list(pb['orig_mask']))
        return state

    def random_neighbor(self, state):
        new_state = [list(m) for m in state]
        candidates = [i for i, pb in enumerate(self.per_bind) if pb['allowed']]
        if not candidates:
            return new_state
        bi = random.choice(candidates)
        pb = self.per_bind[bi]
        op_len = len(new_state[bi])
        if op_len == 0:
            return new_state
        op = random.choices(['flip', 'grow', 'shrink'], weights=[0.5, 0.3, 0.2], k=1)[0]
        if op == 'flip':
            idx = random.choice(list(pb['allowed']))
            new_state[bi][idx] = 1 - new_state[bi][idx]
        elif op == 'grow':
            ones = [i for i, v in enumerate(new_state[bi]) if v == 1]
            if ones:
                seed = random.choice(ones)
                neighbors = [j for a, c in pb['edges'] for j in ([a] if c == seed else ([c] if a == seed else []))]
                neighbors = [j for j in neighbors if j in pb['allowed']]
                if neighbors:
                    k = random.randint(1, min(2, len(neighbors)))
                    for j in random.sample(neighbors, k):
                        new_state[bi][j] = 1
        else:  # shrink
            ones = [i for i, v in enumerate(new_state[bi]) if v == 1 and i in pb['allowed']]
            if ones:
                k = random.randint(1, 1)
                for j in random.sample(ones, k):
                    new_state[bi][j] = 0
        return new_state

    def metrics(self, state):
        total_L = 0
        total_E = 0
        total_C = 0
        total_iface = 0.0
        for m, pb in zip(state, self.per_bind):
            L = sum(1 for v in m if v == 1)
            E = 0
            if pb['edges']:
                ones_set = {i for i, v in enumerate(m) if v == 1}
                for a, c in pb['edges']:
                    if a in ones_set and c in ones_set:
                        E += 1
            C = max(0, L - E)
            L_norm = (L / max(1, pb['mask_len']))
            iface = len(pb['sources']) * L_norm
            total_L += L
            total_E += E
            total_C += C
            total_iface += iface
        return {
            'L': total_L,
            'E': total_E,
            'C': total_C,
            'IFACE': total_iface,
        }

    def cost(self, state, w: BindCostWeights):
        m = self.metrics(state)
        area = w.area_a1 * m['L'] - w.area_a2 * m['E']
        delay = w.delay_d1 * m['C']
        power = w.power_p1 * m['L']
        iface = w.iface_i1 * m['IFACE']
        total = w.wi * area + w.wz * delay + w.w3 * power + w.wa * iface
        return total, {
            'area': area,
            'delay': delay,
            'power': power,
            'interface': iface,
            'L': m['L'], 'E': m['E'], 'C': m['C'], 'IFACE': m['IFACE']
        }


def run_bindmask_anneal(bind_json_path: str,
                         weights: BindCostWeights,
                         initial_temperature: float = 50.0,
                         final_temperature: float = 0.2,
                         cooling_rate: float = 0.95,
                         iterations_per_temp: int = 50,
                         max_iterations: int = 4000,
                         multi_start_runs: int = 3,
                         seed: Optional[int] = None,
                         export_path: Optional[str] = None):
    problem = BindMaskProblem(bind_json_path)
    best_overall = None
    best_overall_cost = float('inf')
    base_seed = seed if seed is not None else random.randint(0, 10**9)
    for r in range(max(1, multi_start_runs)):
        if seed is not None:
            random.seed(base_seed + r)
            try:
                np.random.seed(base_seed + r)
            except Exception:
                pass
        state = problem.initial_state()
        current = [list(m) for m in state]
        current_cost, _ = problem.cost(current, weights)
        best = [list(m) for m in current]
        best_cost = current_cost
        temp = initial_temperature
        iter_cnt = 0
        cost_hist = [current_cost]
        while temp > final_temperature and iter_cnt < max_iterations:
            for _ in range(iterations_per_temp):
                neigh = problem.random_neighbor(current)
                neigh_cost, _ = problem.cost(neigh, weights)
                delta = neigh_cost - current_cost
                if delta < 0 or np.exp(-delta / max(1e-9, temp)) > random.random():
                    current = neigh
                    current_cost = neigh_cost
                    if current_cost < best_cost:
                        best = [list(m) for m in current]
                        best_cost = current_cost
                iter_cnt += 1
                cost_hist.append(current_cost)
            temp *= cooling_rate
        if best_cost < best_overall_cost:
            best_overall = {
                'state': best,
                'cost': best_cost,
                'runs': r + 1,
                'history': cost_hist,
            }
            best_overall_cost = best_cost

    if export_path and best_overall is not None:
        totals = problem.cost(best_overall['state'], weights)[1]
        out_binds = []
        for pb, m in zip(problem.per_bind, best_overall['state']):
            L = sum(1 for v in m if v == 1)
            ones_set = {i for i, v in enumerate(m) if v == 1}
            E = sum(1 for a, c in pb['edges'] if a in ones_set and c in ones_set)
            C = max(0, L - E)
            out_binds.append({
                'dest': pb['dest'],
                'operator_order': list(pb['order']),
                'initial_mask': list(pb['orig_mask']),
                'best_mask': list(m),
                'stats': {'L': L, 'E': E, 'C': C, 'sources': list(pb['sources'])}
            })
        payload = {
            'bind_json': bind_json_path,
            'weights': vars(weights),
            'best_total_cost': best_overall['cost'],
            'totals': totals,
            'binds': out_binds,
        }
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        Path(export_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print('[BIND SA] export =>', export_path)
        return export_path
    return None

    
if __name__ == "__main__":
    # ---------------- 1) 真实图的优化流程 ----------------
    graph_json = Path('results/4004_dfg_linearity_graph.json')
    if graph_json.exists() and nx is not None:
        from analyzers.graph_loader import load_graph_from_json
        g = load_graph_from_json(str(graph_json))
        from partitioning.cost_strategies import get_cost_function  # 局部导入
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
        print('[REAL GRAPH] best_cost=', res.best_cost, 'improve=%.2f%%' % (analysis['cost_improvement'] or 0.0), 'export =>', export_path)
    else:
        print('缺少真实图 JSON: results/4004_dfg_linearity_graph.json，已跳过图级优化。')

    # ---------------- 2) Bind 掩码级的优化流程 ----------------
    # 该部分实现一个简化成本模型：
    # total = wi*Area + wz*Delay + w3*Power + wa*Interface
    # 其中：
    # - Area ~ a1*L - a2*E，L为当前掩码中1的数量（线性算子数），E为可融合边中被激活的条数（两端均为1）
    # - Delay ~ d1*C，C为由1组成的连通分量数量 (近似链深度 proxy)
    # - Power ~ p1*L
    # - Interface ~ i1*(|sources| * L_norm)，sources来自 bind 的跨信号依赖；L_norm=L/max(1,op_count)

    bind_json = Path('results/4004_dfg_bind_masks.json')
    if bind_json.exists():
        # ONN 偏好（优先减少模块数量 C 与接口成本）：
        # - 提高延迟与接口权重 (wz, wa)，并提高 delay_d1/iface_i1
        # - 提高融合奖励 area_a2，降低线性单元与功耗惩罚 (area_a1, power_p1)
        w = BindCostWeights(
            wi=0.7,
            wz=1.3,
            w3=0.3,
            wa=1.4,
            area_a1=0.6,
            area_a2=1.2,
            delay_d1=1.2,
            power_p1=0.3,
            iface_i1=0.8,
        )
        out = run_bindmask_anneal(
            str(bind_json), w,
            initial_temperature=40.0,
            final_temperature=0.5,
            cooling_rate=0.92,
            iterations_per_temp=40,
            max_iterations=2500,
            multi_start_runs=3,
            seed=42,
            export_path='results/4004_bindmask_sa_best.json'
        )
        if out is None:
            print('[BIND SA] 未能生成结果文件')
    else:
        print('缺少 Bind 掩码 JSON: results/4004_dfg_bind_masks.json，已跳过 bind 级优化。')