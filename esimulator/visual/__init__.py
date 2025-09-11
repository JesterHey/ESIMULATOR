"""统一的可视化接口

提供基于 DFG 的图构建与导出：
- visualize_from_dfg: 从 DFG 文本构建图，并导出 DOT/HTML
- export_partition_dot: 从 graph + partition 导出 DOT
- export_comparison_dot: 从两个 partition 对比导出 DOT

说明：该模块封装 src/visual/partition_viz.py 的能力，替换早期零散实现。
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from pathlib import Path
import json

try:
    import networkx as nx
except Exception:
    nx = None  # type: ignore

from analyzers.graph_loader import load_graph_from_json
from .partition_viz import export_partition_dot, export_comparison_dot  # 使用包内实现

__all__ = [
    'visualize_from_dfg',
    'export_partition_dot',
    'export_comparison_dot',
]


def _build_graph_from_dfg(dfg_path: str):
    """将 DFG 文本先通过已存在的分析流程转为 graph json，再加载为 nx.DiGraph。
    这里假设外部流程已生成 results/*_linearity_graph.json，
    若不存在，则仅报错提示用户先运行分析流程。
    """
    # 推断结果 JSON 路径（与项目现有流程保持一致）
    json_path = Path('results/4004_dfg_linearity_graph.json')
    if not json_path.exists():
        raise FileNotFoundError('缺少图 JSON: results/4004_dfg_linearity_graph.json，请先运行线性分析生成该文件。')
    return load_graph_from_json(str(json_path))


def visualize_from_dfg(
    dfg_path: str,
    output_dir: str,
    *,
    stem: Optional[str] = None,
    focus: Optional[str] = None,
    depth: int = 2,
    keep: Optional[str] = None,  # 'linear' | 'nonlinear' | None
    html: bool = False,
    dot: bool = True,
) -> Dict[str, Any]:
    """从 DFG 文件生成可视化产物（封装 DOT 导出；HTML 预留）。

    返回 { 'dot': <path or None>, 'html': <path or None>, 'metrics': {...} }
    """
    g = _build_graph_from_dfg(dfg_path)

    # 简单子图过滤（可选）：按线性/非线性、焦点/深度过滤
    def _filter_graph(graph):
        H = graph.copy()
        # 线性/非线性过滤
        if keep in ('linear', 'nonlinear'):
            target = (keep == 'linear')
            to_remove = [n for n, a in H.nodes(data=True) if bool(a.get('is_linear', False)) != target]
            H.remove_nodes_from(to_remove)
        # 焦点过滤：向前 depth 层
        if focus and focus in H:
            keep_nodes = set([focus])
            frontier = [focus]
            for _ in range(max(0, depth)):
                next_frontier = []
                for u in frontier:
                    for v in H.successors(u):
                        if v not in keep_nodes:
                            keep_nodes.add(v)
                            next_frontier.append(v)
                frontier = next_frontier
            # 反向保留 predecessors
            rev_frontier = [focus]
            for _ in range(max(0, depth)):
                next_rev = []
                for v in rev_frontier:
                    for u in H.predecessors(v):
                        if u not in keep_nodes:
                            keep_nodes.add(u)
                            next_rev.append(u)
                rev_frontier = next_rev
            remove_nodes = [n for n in H.nodes() if n not in keep_nodes]
            H.remove_nodes_from(remove_nodes)
        return H

    Gv = _filter_graph(g)

    output = {
        'dot': None,
        'html': None,
        'metrics': {
            'nodes': Gv.number_of_nodes(),
            'edges': Gv.number_of_edges(),
            'linear_nodes': sum(1 for n in Gv.nodes() if Gv.nodes[n].get('is_linear', False)),
        }
    }

    # 导出 DOT
    if dot:
        name = stem or Path(dfg_path).stem
        dot_path = Path(output_dir) / f"{name}.dot"
        # 尝试加载最佳分区以增强可视化（若存在）
        cost_breakdown = None
        strategy = None
        best_json = Path('results/4004_best_partition.json')
        if best_json.exists():
            try:
                best = json.loads(best_json.read_text(encoding='utf-8'))
                part = best.get('partition', {})
                cost_breakdown = best.get('cost_breakdown')
                strategy = best.get('strategy')
            except Exception:
                part = {n: (1 if Gv.nodes[n].get('is_linear', False) else 0) for n in Gv.nodes()}
        else:
            part = {n: (1 if Gv.nodes[n].get('is_linear', False) else 0) for n in Gv.nodes()}
        export_partition_dot(Gv, part, str(dot_path), cost_breakdown=cost_breakdown, title='DFG Partition', strategy=strategy)
        output['dot'] = str(dot_path)

    # 预留 HTML（后续如需添加交互式可视化）
    if html:
        # 暂不实现，返回占位 None
        output['html'] = None

    return output
