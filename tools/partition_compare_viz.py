#!/usr/bin/env python3
"""
分区对比可视化（前/后）：

输入：
  - --edges-json 边列表 JSON（形如 {"edges": [["u","v"], ...]}）
  - --before 前一版本分区映射 JSON（node -> part）
  - --after  后一版本分区映射 JSON（node -> part）
  - --bind-masks 可选，bind 掩码 JSON（用于线性/非线性着色）
  - --out 输出目录

输出：
  - before.dot / after.dot（按分区 cluster 分组，跨分区边保留）
  - compare_metrics.json（节点数、分区数、割边数、变化情况等）
  - compare.html（简易对比页，引用 DOT→PNG 后的图片占位）

注意：
  - 若需要 PNG，请先安装 graphviz 并手动或脚本化执行 dot -Tpng *.dot -O
  - 分区 JSON 可为 {"node": part, ...} 或 {"part": [nodes...] }，脚本将自动兼容。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set


def load_edges(p: Path) -> List[Tuple[str, str]]:
    data = json.loads(p.read_text(encoding='utf-8'))
    edges = data.get('edges')
    if isinstance(edges, list) and edges and isinstance(edges[0], list):
        return [(str(u), str(v)) for u, v in edges]
    raise ValueError('edges-json 格式错误，需为 {"edges": [[u,v], ...]}')


def to_node_part_map(obj: dict) -> Dict[str, str]:
    # 兼容两种：node->part 或 part->list[node]
    if not obj:
        return {}
    # 检测 node->part 形态
    sample_v = next(iter(obj.values()))
    if isinstance(sample_v, (str, int)):
        return {str(k): str(v) for k, v in obj.items()}
    # 检测 part->list 形态
    mp: Dict[str, str] = {}
    for part, nodes in obj.items():
        for n in nodes:
            mp[str(n)] = str(part)
    return mp


def load_partitions(p: Path) -> Dict[str, str]:
    return to_node_part_map(json.loads(p.read_text(encoding='utf-8')))


def load_linearity(bind_masks_path: Path | None) -> Dict[str, bool]:
    if not bind_masks_path or not bind_masks_path.exists():
        return {}
    data = json.loads(bind_masks_path.read_text(encoding='utf-8'))
    res: Dict[str, bool] = {}
    for b in data.get('binds', []):
        name = str(b.get('name'))
        is_lin = bool(b.get('is_linear'))
        res[name] = is_lin
    return res


def cut_edges(edges: List[Tuple[str, str]], parts: Dict[str, str]) -> int:
    c = 0
    for u, v in edges:
        if parts.get(u) != parts.get(v):
            c += 1
    return c


def part_stats(parts: Dict[str, str]) -> Dict[str, int]:
    cnt: Dict[str, int] = {}
    for n, p in parts.items():
        cnt[p] = cnt.get(p, 0) + 1
    return cnt


_PALETTE = [
    '#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#f472b6', '#f59e0b', '#10b981', '#22d3ee', '#fb7185'
]


def to_dot(edges: List[Tuple[str, str]], parts: Dict[str, str], linearity: Dict[str, bool], title: str) -> str:
    # 分区 -> 颜色
    part_ids = sorted(set(parts.values()))
    color_map = {pid: _PALETTE[i % len(_PALETTE)] for i, pid in enumerate(part_ids)}

    # 分区节点
    members: Dict[str, List[str]] = {pid: [] for pid in part_ids}
    for n, pid in parts.items():
        members.setdefault(pid, []).append(n)

    lines: List[str] = ["digraph G {", "  rankdir=LR;", f"  labelloc=\"t\"; label=\"{title}\";"]
    lines.append("  node [shape=ellipse, style=filled, fillcolor=white];")

    # cluster per partition
    for pid in part_ids:
        color = color_map[pid]
        lines.append(f"  subgraph cluster_{pid} {{")
        lines.append(f"    label=\"part {pid}\"; color=\"{color}\"; style=rounded;")
        for n in sorted(members.get(pid, [])):
            if n in linearity:
                # 线性浅色，非线性深色
                fill = color if not linearity[n] else '#ffffff'
            else:
                fill = '#ffffff'
            lines.append(f"    \"{n}\" [fillcolor=\"{fill}\"];")
        lines.append("  }")

    # edges
    for u, v in edges:
        ecolor = '#94a3b8' if parts.get(u) == parts.get(v) else '#ef4444'
        lines.append(f"  \"{u}\" -> \"{v}\" [color=\"{ecolor}\"];")

    lines.append("}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description='分区前后对比可视化')
    ap.add_argument('--edges-json', required=True, help='边列表 JSON：{"edges": [["u","v"], ...]}')
    ap.add_argument('--before', required=True, help='前一版本分区 JSON（node->part 或 part->[nodes]）')
    ap.add_argument('--after', required=True, help='后一版本分区 JSON（node->part 或 part->[nodes]）')
    ap.add_argument('--bind-masks', help='可选：bind 掩码 JSON（用于线性/非线性着色）')
    ap.add_argument('--out', required=True, help='输出目录')
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    edges = load_edges(Path(args.edges_json))
    parts_before = load_partitions(Path(args.before))
    parts_after = load_partitions(Path(args.after))
    linearity = load_linearity(Path(args.bind_masks)) if args.bind_masks else {}

    # 对齐节点集合（仅考虑出现在边或分区映射中的节点）
    nodes: Set[str] = set()
    nodes |= set(n for e in edges for n in e)
    nodes |= set(parts_before.keys()) | set(parts_after.keys())
    # 对缺失分区的节点填充“unknown”
    parts_before = {n: parts_before.get(n, 'unknown') for n in nodes}
    parts_after = {n: parts_after.get(n, 'unknown') for n in nodes}

    # 计算指标
    cut_bef = cut_edges(edges, parts_before)
    cut_aft = cut_edges(edges, parts_after)
    stat_b = part_stats(parts_before)
    stat_a = part_stats(parts_after)
    moved = sum(1 for n in nodes if parts_before.get(n) != parts_after.get(n))

    metrics = {
        'nodes': len(nodes),
        'edges': len(edges),
        'partitions_before': len(stat_b),
        'partitions_after': len(stat_a),
        'cut_edges_before': cut_bef,
        'cut_edges_after': cut_aft,
        'cut_delta': cut_aft - cut_bef,
        'moved_nodes': moved,
        'size_before': stat_b,
        'size_after': stat_a,
    }

    # 生成 DOT
    dot_before = to_dot(edges, parts_before, linearity, 'Before Partition')
    dot_after = to_dot(edges, parts_after, linearity, 'After Partition')
    (out_dir / 'before.dot').write_text(dot_before, encoding='utf-8')
    (out_dir / 'after.dot').write_text(dot_after, encoding='utf-8')

    # 写指标
    (out_dir / 'compare_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')

    # 简易对比页（PNG 需要用户渲染后替换引用路径）
    html = f"""
<!doctype html>
<html lang=\"zh\"><head><meta charset=\"utf-8\"><title>分区对比</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}} .col{{float:left;width:48%;margin:1%;}} img{{max-width:100%;border:1px solid #ddd;border-radius:6px;}} pre{{background:#f8fafc;padding:8px;border-radius:6px;overflow:auto;}}</style>
</head><body>
<h2>分区前后对比</h2>
<div class=\"col\"><h3>Before</h3><p><em>请先用 graphviz 生成 before.dot.png</em></p><img src=\"before.dot.png\" alt=\"before\"></div>
<div class=\"col\"><h3>After</h3><p><em>请先用 graphviz 生成 after.dot.png</em></p><img src=\"after.dot.png\" alt=\"after\"></div>
<div style=\"clear:both\"></div>
<h3>指标 (compare_metrics.json)</h3>
<pre>{json.dumps(metrics, ensure_ascii=False, indent=2)}</pre>
</body></html>
"""
    (out_dir / 'compare.html').write_text(html, encoding='utf-8')

    print('[OK] 已生成:')
    print('  -', out_dir / 'before.dot')
    print('  -', out_dir / 'after.dot')
    print('  -', out_dir / 'compare_metrics.json')
    print('  -', out_dir / 'compare.html')
    print('提示: 渲染 PNG')
    print('  dot -Tpng', str(out_dir / 'before.dot'), '-O')
    print('  dot -Tpng', str(out_dir / 'after.dot'), '-O')


if __name__ == '__main__':
    main()
