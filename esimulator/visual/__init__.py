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

# 尝试使用 src.analyzers 提供的装载函数；若不可用则内联一个简化版
try:
    from src.analyzers.graph_loader import load_graph_from_json  # type: ignore
except Exception:
    def load_graph_from_json(json_path: str):  # fallback
        if nx is None:
            raise RuntimeError("需要安装 networkx 才能加载图: pip install networkx")
        data = json.loads(Path(json_path).read_text(encoding='utf-8'))
        G = nx.DiGraph()
        for name, attrs in data['nodes'].items():
            G.add_node(name, **attrs)
        for src, dst in data['edges']:
            if src not in G:
                G.add_node(src, is_linear=False, reason='external', operators=[], expression_type='external')
            if dst not in G:
                G.add_node(dst, is_linear=False, reason='external', operators=[], expression_type='external')
            G.add_edge(src, dst)
        return G
# 优先使用包内基于 networkx 的实现；若不可用则提供简化导出
try:
    from .partition_viz import export_partition_dot, export_comparison_dot  # type: ignore
except Exception:
    export_comparison_dot = None  # type: ignore

    def export_partition_dot(graph_data: dict,
                             partition: dict,
                             output_path: str,
                             *,
                             cost_breakdown=None,
                             title: str = 'Partition View',
                             strategy: str | None = None,
                             highlight_linear_cluster: bool = True,
                             add_legend: bool = True) -> str:
        # graph_data: { 'nodes': {name: {is_linear: bool, ...}}, 'edges': [(u,v), ...] }
        DOMAIN_COLORS = {0: '#cfe8ff', 1: '#ffe6b3'}
        NODE_SHAPES = {True: 'box', False: 'ellipse'}
        def _esc(s: str) -> str:
            return s.replace('"', '\\"')
        lines = ["digraph G {", '  rankdir=LR;']
        if title:
            label_lines = [title]
            if strategy:
                label_lines.append(f'Strategy: {strategy}')
            if cost_breakdown:
                parts = []
                for k in ['cross', 'penalty', 'reward', 'balance', 'total']:
                    if isinstance(cost_breakdown, dict) and k in cost_breakdown:
                        parts.append(f"{k}={cost_breakdown[k]}")
                if parts:
                    label_lines.append(' / '.join(parts))
            lines.append('  labelloc="t";')
            _label_text = _esc("\n".join(label_lines))
            lines.append(f'  label="{_label_text}";')
        lines.append('  node [style=filled, fontname="Helvetica"];')
        # clusters
        clusters: dict[int, list[str]] = {0: [], 1: []}
        for n in graph_data['nodes'].keys():
            d = int(partition.get(n, 0))
            clusters.setdefault(d, []).append(n)
        for d, nodes in clusters.items():
            color = DOMAIN_COLORS.get(d, '#dddddd')
            lines.append(f'  subgraph cluster_{d} {{')
            lines.append(f'    label="Domain {d}";')
            lines.append('    color="#999999";')
            for n in nodes:
                is_lin = bool(graph_data['nodes'][n].get('is_linear', False))
                shape = NODE_SHAPES[is_lin]
                short = n.split('.')[-1]
                tag = 'L' if is_lin else 'N'
                lines.append(f'    "{_esc(n)}" [label="{_esc(short)}\\n({tag})", shape={shape}, fillcolor="{color}"];')
            lines.append('  }')
        # edges
        for (u, v) in graph_data['edges']:
            pu = partition.get(u, 0)
            pv = partition.get(v, 0)
            is_cross = pu != pv
            is_lin_pair = (graph_data['nodes'].get(u, {}).get('is_linear') and
                           graph_data['nodes'].get(v, {}).get('is_linear') and not is_cross)
            color = '#d62728' if is_cross else ('#2ca02c' if (highlight_linear_cluster and is_lin_pair) else '#bbbbbb')
            penwidth = '2' if is_cross else ('1.5' if is_lin_pair else '1')
            attr = [f'color="{color}"', f'penwidth={penwidth}']
            if is_cross:
                src_tag = 'L' if graph_data['nodes'].get(u, {}).get('is_linear', False) else 'N'
                attr.append(f'label="{src_tag}"')
                attr.append('fontcolor="#444444"')
                attr.append('fontsize=10')
            _attr_str = ', '.join(attr)
            lines.append(f'  "{_esc(u)}" -> "{_esc(v)}" [{_attr_str}];')
        if add_legend:
            lines.append('  subgraph cluster_legend {')
            lines.append('    label="Legend";')
            lines.append('    fontsize=10;')
            lines.append('    color="#666666";')
            lines.append('    "LEG_LIN" [label="Linear (L)", shape=box, style=filled, fillcolor="#e6f2ff"];')
            lines.append('    "LEG_NON" [label="Nonlinear (N)", shape=ellipse, style=filled, fillcolor="#fff2db"];')
            lines.append('    "LEG_CROSS" [label="Cross Edge", shape=plaintext];')
            lines.append('    "LEG_REWARD" [label="Linear Same-Domain Edge", shape=plaintext];')
            lines.append('    "LEG_CROSS" -> "LEG_REWARD" [color="#d62728", penwidth=2];')
            lines.append('    "LEG_REWARD" -> "LEG_NON" [color="#2ca02c", penwidth=1.5];')
            lines.append('  }')
        lines.append('}')
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding='utf-8')
        return str(path)

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
    if nx is None:
        # 返回原始 JSON 数据以供简化导出
        return json.loads(json_path.read_text(encoding='utf-8'))
    else:
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
    if nx is not None:
        def _filter_graph(graph):
            H = graph.copy()
            if keep in ('linear', 'nonlinear'):
                target = (keep == 'linear')
                to_remove = [n for n, a in H.nodes(data=True) if bool(a.get('is_linear', False)) != target]
                H.remove_nodes_from(to_remove)
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
    else:
        # 简化版过滤（基于 JSON 数据）
        data = g
        nodes = set(data['nodes'].keys())
        edges = list(data['edges'])
        if keep in ('linear', 'nonlinear'):
            target = (keep == 'linear')
            nodes = {n for n in nodes if bool(data['nodes'][n].get('is_linear', False)) == target}
            edges = [(u, v) for (u, v) in edges if u in nodes and v in nodes]
        if focus and focus in data['nodes']:
            succ = {}
            pred = {}
            for u, v in data['edges']:
                succ.setdefault(u, []).append(v)
                pred.setdefault(v, []).append(u)
            keep_nodes = {focus}
            frontier = [focus]
            for _ in range(max(0, depth)):
                next_frontier = []
                for u in frontier:
                    for v in succ.get(u, []):
                        if v not in keep_nodes:
                            keep_nodes.add(v)
                            next_frontier.append(v)
                frontier = next_frontier
            rev_frontier = [focus]
            for _ in range(max(0, depth)):
                next_rev = []
                for v in rev_frontier:
                    for u in pred.get(v, []):
                        if u not in keep_nodes:
                            keep_nodes.add(u)
                            next_rev.append(u)
                rev_frontier = next_rev
            nodes = {n for n in nodes if n in keep_nodes}
            edges = [(u, v) for (u, v) in edges if u in nodes and v in nodes]
        Gv = {'nodes': {n: data['nodes'][n] for n in nodes}, 'edges': edges}

    if isinstance(Gv, dict):
        nodes_count = len(Gv['nodes'])
        edges_count = len(Gv['edges'])
        linear_count = sum(1 for n, a in Gv['nodes'].items() if a.get('is_linear', False))
    else:
        nodes_count = Gv.number_of_nodes()
        edges_count = Gv.number_of_edges()
        linear_count = sum(1 for _, a in Gv.nodes(data=True) if a.get('is_linear', False))

    metrics = {
        'nodes': nodes_count,
        'edges': edges_count,
        'linear_nodes': linear_count,
    }

    output = {'dot': None, 'html': None, 'metrics': metrics}

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
                if isinstance(Gv, dict):
                    part = {n: (1 if Gv['nodes'][n].get('is_linear', False) else 0) for n in Gv['nodes']}
                else:
                    part = {n: (1 if a.get('is_linear', False) else 0) for n, a in Gv.nodes(data=True)}
        else:
            if isinstance(Gv, dict):
                part = {n: (1 if Gv['nodes'][n].get('is_linear', False) else 0) for n in Gv['nodes']}
            else:
                part = {n: (1 if a.get('is_linear', False) else 0) for n, a in Gv.nodes(data=True)}
        # 调用对应导出器
        export_partition_dot(Gv, part, str(dot_path), cost_breakdown=cost_breakdown, title='DFG Partition', strategy=strategy)
        output['dot'] = str(dot_path)

    # 预留 HTML（后续如需添加交互式可视化）
    if html:
        # 暂不实现，返回占位 None
        output['html'] = None

    return output
