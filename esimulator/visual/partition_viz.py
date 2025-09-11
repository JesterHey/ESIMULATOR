"""分区结果可视化 (Graphviz DOT 导出)

功能:
1. export_partition_dot: 依据单个分区生成 .dot 文件 (含成本分解可选注释)
2. export_comparison_dot: 对比两个分区 (如 初始 vs 最优), 突出变化节点与跨域边

设计要点:
 - 二域分区使用 cluster0 / cluster1 子图分组, 颜色区分
 - 线性节点 与 非线性节点使用不同形状 (box=线性, ellipse=非线性)
 - 跨域边标红, 同域边淡灰；线性同域奖励边标绿
 - mixed 策略下可在图中注释各成本分量
 - 对比模式: 变化节点加粗边框 (penwidth=2 peripheries=2) 并在标签后缀 *
"""
from __future__ import annotations
from typing import Dict, Optional, Any
import networkx as nx
from pathlib import Path


DOMAIN_COLORS = {0: '#cfe8ff', 1: '#ffe6b3'}  # 浅蓝 / 浅金
NODE_SHAPES = {True: 'box', False: 'ellipse'}  # 线性 / 非线性


def _escape(s: str) -> str:
    return s.replace('"', '\"')


def export_partition_dot(graph: nx.DiGraph,
                         partition: Dict[str, int],
                         output_path: str,
                         *,
                         cost_breakdown: Optional[Dict[str, Any]] = None,
                         title: str = 'Partition View',
                         strategy: Optional[str] = None,
                         highlight_linear_cluster: bool = True,
                         add_legend: bool = True) -> str:
    """导出单分区 DOT 文件.

    参数:
        graph: networkx DiGraph (需含 is_linear 属性)
        partition: 节点->域 (0/1)
        output_path: 目标 .dot 文件路径
        cost_breakdown: 可选成本分解 (mixed 输出)
        title: 图标题
        strategy: 策略名 (显示用)
    返回: 写入文件的绝对路径
    """
    lines = ["digraph G {", '  rankdir=LR;']
    if title:
        label_lines = [title]
        if strategy:
            label_lines.append(f'Strategy: {strategy}')
        if cost_breakdown:
            parts = []
            for k in ['cross', 'penalty', 'reward', 'balance', 'total']:
                if k in cost_breakdown:
                    parts.append(f"{k}={cost_breakdown[k]}")
            label_lines.append(' / '.join(parts))
        label_text = "\n".join(label_lines)
        lines.append('  labelloc="t";')
        lines.append(f'  label="{_escape(label_text)}";')
    lines.append('  node [style=filled, fontname="Helvetica"];')

    # 子图 cluster0 / cluster1
    clusters = {0: [], 1: []}
    for n in graph.nodes():
        d = int(partition.get(n, 0))
        clusters.setdefault(d, []).append(n)

    for d, nodes in clusters.items():
        color = DOMAIN_COLORS.get(d, '#dddddd')
        lines.append(f'  subgraph cluster_{d} {{')
        lines.append(f'    label="Domain {d}";')
        lines.append('    color="#999999";')
        for n in nodes:
            is_lin = bool(graph.nodes[n].get('is_linear', False))
            shape = NODE_SHAPES[is_lin]
            fill = color
            # 节点标签: 名称最后一段 (去掉层级前缀) + L/N 标记
            short = n.split('.')[-1]
            tag = 'L' if is_lin else 'N'
            lines.append(f'    "{_escape(n)}" [label="{_escape(short)}\n({tag})", shape={shape}, fillcolor="{fill}"];')
        lines.append('  }')

    # 边
    for u, v in graph.edges():
        pu = partition.get(u, 0)
        pv = partition.get(v, 0)
        is_cross = pu != pv
        # 线性同域奖励边高亮
        is_lin_pair = (graph.nodes[u].get('is_linear') and graph.nodes[v].get('is_linear') and not is_cross)
        color = '#d62728' if is_cross else ('#2ca02c' if (highlight_linear_cluster and is_lin_pair) else '#bbbbbb')
        penwidth = '2' if is_cross else ('1.5' if is_lin_pair else '1')
        attr = [f'color="{color}"', f'penwidth={penwidth}']
        src_tag = 'L' if graph.nodes[u].get('is_linear', False) else 'N'
        if is_cross:
            attr.append(f'label="{src_tag}"')
            attr.append('fontcolor="#444444"')
            attr.append('fontsize=10')
        lines.append(f'  "{_escape(u)}" -> "{_escape(v)}" [{" ".join(attr)}];')

    # 图例 (可选)
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
    return str(path.resolve())


def export_comparison_dot(graph: nx.DiGraph,
                          partition_a: Dict[str, int],
                          partition_b: Dict[str, int],
                          output_path: str,
                          label_a: str = 'A',
                          label_b: str = 'B') -> str:
    """导出两个分区对比 DOT.

    节点样式:
      - 依据 partition_b 着色 (视为“目标/优化后”)
      - 若 domain 发生变化 (partition_a[n] != partition_b[n]):
            * 加粗外框 penwidth=2, peripheries=2, 标签后缀 *
    边样式:
      - 仍基于 partition_b 判定跨域 (红=跨域, 灰=同域)
    """
    lines = ['digraph G {', '  rankdir=LR;', '  labelloc="t";',
             f'  label="Partition Comparison: {label_a} -> {label_b}";',
             '  node [style=filled, fontname="Helvetica"];']

    for n in graph.nodes():
        d_new = int(partition_b.get(n, 0))
        d_old = int(partition_a.get(n, d_new))
        changed = d_new != d_old
        is_lin = bool(graph.nodes[n].get('is_linear', False))
        shape = NODE_SHAPES[is_lin]
        fill = DOMAIN_COLORS.get(d_new, '#dddddd')
        short = n.split('.')[-1]
        tag = 'L' if is_lin else 'N'
        label = f'{short}\\n({tag},{d_old}->{d_new})'
        if changed:
            label += '*'
        attrs = [f'label="{_escape(label)}"', f'shape={shape}', f'fillcolor="{fill}"']
        if changed:
            attrs.append('penwidth=2')
            attrs.append('peripheries=2')
        lines.append(f'  "{_escape(n)}" [{" ".join(attrs)}];')

    for u, v in graph.edges():
        pu = partition_b.get(u, 0)
        pv = partition_b.get(v, 0)
        is_cross = pu != pv
        color = '#d62728' if is_cross else '#bbbbbb'
        penwidth = '2' if is_cross else '1'
        src_tag = 'L' if graph.nodes[u].get('is_linear', False) else 'N'
        attr = [f'color="{color}"', f'penwidth={penwidth}']
        if is_cross:
            attr.append(f'label="{src_tag}"')
            attr.append('fontsize=10')
            attr.append('fontcolor="#444444"')
        lines.append(f'  "{_escape(u)}" -> "{_escape(v)}" [{" ".join(attr)}];')

    lines.append('}')
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding='utf-8')
    return str(path.resolve())


__all__ = [
    'export_partition_dot',
    'export_comparison_dot'
]
