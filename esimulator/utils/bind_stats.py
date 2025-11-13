#!/usr/bin/env python3
"""
Bind 掩码 JSON 统计工具
用法:
  python3 -m esimulator.utils.bind_stats <path/to/*_bind_masks.json>
"""

from __future__ import annotations
import json
import sys
from collections import Counter
from statistics import mean, median
from typing import Any, Dict, List


def hist_bucket(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if 2 <= n <= 3:
        return "2-3"
    if 4 <= n <= 7:
        return "4-7"
    return "8+"


def summarize_bind_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    binds: List[Dict[str, Any]] = data.get('binds', [])
    total_binds = len(binds)
    kinds = Counter(b.get('bind_kind', 'unknown') for b in binds)
    trivial = sum(1 for b in binds if b.get('is_trivial', False))
    maskable_counts = [int(b.get('maskable_count', len(b.get('workset_order', [])))) for b in binds]
    maskable_hist = Counter(hist_bucket(x) for x in maskable_counts)
    workset_total = sum(maskable_counts)

    intrinsic_ones = 0
    mask_ones = 0
    fusable_edges = 0
    op_counts = []
    for b in binds:
        w_im = b.get('workset_intrinsic_mask', [])
        w_mk = b.get('workset_mask', [])
        intrinsic_ones += sum(int(x) for x in w_im)
        mask_ones += sum(int(x) for x in w_mk)
        fusable_edges += len(b.get('fusable_adj', []))
        op_counts.append(int(b.get('operator_count', 0)))

    intrinsic_ratio = (intrinsic_ones / workset_total) if workset_total else 0.0
    mask_ratio = (mask_ones / workset_total) if workset_total else 0.0

    result = {
        'file': path,
        'total_binds': total_binds,
        'kinds': dict(kinds),
        'trivial_binds': trivial,
        'maskable_count': {
            'mean': float(mean(maskable_counts)) if maskable_counts else 0.0,
            'median': float(median(maskable_counts)) if maskable_counts else 0.0,
            'hist': dict(maskable_hist),
        },
        'workset_total': workset_total,
        'intrinsic_ratio': intrinsic_ratio,
        'mask_ratio': mask_ratio,
        'fusable_edges_per_bind': (fusable_edges / total_binds) if total_binds else 0.0,
        'operator_count': {
            'mean': float(mean(op_counts)) if op_counts else 0.0,
            'median': float(median(op_counts)) if op_counts else 0.0,
        },
        'top_maskable_binds': [
            {
                'dest': b.get('dest'),
                'maskable_count': int(b.get('maskable_count', len(b.get('workset_order', [])))),
                'bind_kind': b.get('bind_kind', 'unknown')
            }
            for b in sorted(binds, key=lambda x: int(x.get('maskable_count', len(x.get('workset_order', [])))), reverse=True)[:10]
        ]
    }
    return result


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("用法: python3 -m esimulator.utils.bind_stats <path/to/*_bind_masks.json>")
        return 2
    path = argv[1]
    stats = summarize_bind_json(path)
    # 简洁输出
    print(f"== {stats['file']} ==")
    print(f"binds: {stats['total_binds']} | trivial: {stats['trivial_binds']} | kinds: {stats['kinds']}")
    mc = stats['maskable_count']
    print(f"maskable_count mean/median: {mc['mean']:.2f}/{mc['median']:.2f} | hist: {mc['hist']}")
    print(f"workset_total: {stats['workset_total']} | intrinsic_ratio: {stats['intrinsic_ratio']:.2%} | mask_ratio: {stats['mask_ratio']:.2%}")
    print(f"fusable_edges_per_bind: {stats['fusable_edges_per_bind']:.2f} | operator_count mean/median: {stats['operator_count']['mean']:.2f}/{stats['operator_count']['median']:.2f}")
    print("top_maskable_binds:")
    for item in stats['top_maskable_binds']:
        print(f"  - {item['dest']}: {item['maskable_count']} ({item['bind_kind']})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
