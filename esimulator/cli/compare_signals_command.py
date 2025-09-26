#!/usr/bin/env python3
"""
比较 Verilog/DFG/导出绑定 中的所有信号覆盖与行号情况
生成文本与 JSON 报告，帮助核对“所有信号均被标注行号/operator/掩码”。
"""
from __future__ import annotations
import os
import sys
import json
from typing import Any, Dict, List, Set


def _collect_sources_from_binds(binds: List[Dict]) -> Set[str]:
    s: Set[str] = set()
    for b in binds:
        for src in b.get('sources', []) or []:
            if isinstance(src, str):
                s.add(src)
    return s


def run_compare_signals(args: Any) -> None:
    """执行全量信号对比。

    输入：
      - dfg_file: DFG 文件
      - verilog_file: Verilog 文件
      - module_prefix: 模块前缀（如 'alu.'）
      - output: 输出目录
    输出：
      - <stem>_signal_compare.txt 文本报告
      - <stem>_signal_compare.json 结构化结果
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

    from src.analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer
    from esimulator.utils import verilog_parser

    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到 DFG 文件 {args.dfg_file}")
        return
    if not args.verilog_file or not os.path.exists(args.verilog_file):
        print("错误: 需要 --verilog-file 指定 Verilog 文件且存在")
        return

    os.makedirs(args.output, exist_ok=True)

    # 1) 解析 Verilog 行号
    vmap: Dict[str, int] = verilog_parser.parse_verilog_for_line_numbers(args.verilog_file, args.module_prefix or "")
    verilog_signals = set(vmap.keys())

    # 2) 运行增强版解析器，拿到 binds（含行号与合成条目）
    analyzer = CorrectedLinearityAnalyzer(
        linearity_mode=getattr(args, 'linearity_mode', 'arith'),
        verilog_file=args.verilog_file,
        module_prefix=args.module_prefix or "",
    )
    analyzer.bind_payloads = []
    analyzer.analyze_dfg_file(args.dfg_file)
    analyzer._ensure_verilog_signal_coverage()  # 覆盖无 bind 的参与信号
    binds: List[Dict] = analyzer.bind_payloads

    # 仅保留字符串类型的 dest
    bind_dests: Set[str] = {str(b.get('dest')) for b in binds if isinstance(b.get('dest'), str)}
    bind_sources = _collect_sources_from_binds(binds)
    all_union: Set[str] = set()
    all_union |= set(verilog_signals)
    all_union |= set(bind_dests)
    all_union |= set(bind_sources)

    # 3) 构建每个信号的对比条目
    by_name: Dict[str, Dict] = {}
    # 索引 binds 以便快速查找
    dest2bind: Dict[str, Dict] = {str(b.get('dest')): b for b in binds if isinstance(b.get('dest'), str)}

    for name in sorted(all_union):
        in_verilog = name in verilog_signals
        as_bind_dest = name in bind_dests
        as_source = name in bind_sources
        bind = dest2bind.get(name)
        entry = {
            'name': name,
            'in_verilog': in_verilog,
            'as_bind_dest': as_bind_dest,
            'as_source': as_source,
            'has_payload_entry': bool(bind is not None),
            'bind_kind': (bind.get('bind_kind') if bind else None),
            'dest_location': (bind.get('dest_location') if bind else None),
            'source_locations_complete': None,
            'operator_types': (bind.get('operator_types') if bind else None),
            'usage_operator_types': (bind.get('usage_operator_types') if bind else None),
            'maskable_count': (bind.get('maskable_count') if bind else None),
            'is_trivial': (bind.get('is_trivial') if bind else None),
        }
        if bind is not None:
            srcs = bind.get('sources') or []
            src_locs = bind.get('source_locations') or []
            complete = True
            for s, loc in zip(srcs, src_locs):
                # 常量允许为 None；普通信号若在 verilog 出现但 loc 仍 None，记为不完整
                if isinstance(s, str) and not s.startswith('CONST('):
                    if s in verilog_signals and loc is None:
                        complete = False
            entry['source_locations_complete'] = complete
        by_name[name] = entry

    # 4) 统计汇总
    summary = {
        'total_names': len(all_union),
        'verilog_only': sorted([n for n in all_union if n in verilog_signals and n not in bind_dests and n not in bind_sources]),
    'bind_only_dests': sorted([n for n in bind_dests if isinstance(n, str) and n not in verilog_signals]),
        'bind_only_sources': sorted([n for n in bind_sources if n not in verilog_signals and not n.startswith('CONST(')]),
        'missing_line_for_bind_dests': sorted([
            n for n in bind_dests
            if isinstance(n, str) and ((dest2bind.get(n) or {}).get('dest_location') is None) and n in verilog_signals
        ]),
        'bind_with_incomplete_source_locations': sorted([n for n, e in by_name.items() if e.get('as_bind_dest') and e.get('source_locations_complete') is False]),
        'verilog_signals': len(verilog_signals),
        'bind_count': len(binds),
    }

    # 5) 输出
    stem = os.path.splitext(os.path.basename(args.dfg_file))[0]
    txt_path = os.path.join(args.output, f"{stem}_signal_compare.txt")
    json_path = os.path.join(args.output, f"{stem}_signal_compare.json")

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"信号对比报告 (DFG vs Verilog)\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Verilog 文件: {args.verilog_file}\n")
        f.write(f"DFG 文件: {args.dfg_file}\n")
        f.write(f"模块前缀: {args.module_prefix or ''}\n\n")
        f.write("概要:\n")
        f.write(f"  总信号名(并集): {summary['total_names']}\n")
        f.write(f"  Verilog 提取信号: {summary['verilog_signals']}\n")
        f.write(f"  导出绑定条目: {summary['bind_count']}\n")
        f.write(f"  仅存在于 Verilog 的信号: {len(summary['verilog_only'])}\n")
        f.write(f"  作为 bind 目标但无 Verilog 行号的: {len(summary['missing_line_for_bind_dests'])}\n")
        f.write(f"  绑定中存在源行号不完整的: {len(summary['bind_with_incomplete_source_locations'])}\n\n")
        if summary['verilog_only']:
            f.write("仅存在于 Verilog 的信号(未参与 DFG):\n")
            for n in summary['verilog_only'][:200]:
                f.write(f"  - {n}\n")
            if len(summary['verilog_only']) > 200:
                f.write(f"  ... 以及 {len(summary['verilog_only'])-200} 个\n")
            f.write("\n")
        if summary['missing_line_for_bind_dests']:
            f.write("应有行号但缺失的 bind 目标(出现在 Verilog):\n")
            for n in summary['missing_line_for_bind_dests']:
                f.write(f"  - {n}\n")
            f.write("\n")
        if summary['bind_with_incomplete_source_locations']:
            f.write("源行号不完整(某些源在 Verilog 出现但未标注行号):\n")
            for n in summary['bind_with_incomplete_source_locations']:
                f.write(f"  - {n}\n")
            f.write("\n")

    result = {
        'verilog_file': args.verilog_file,
        'dfg_file': args.dfg_file,
        'module_prefix': args.module_prefix or '',
        'summary': summary,
        'by_name': by_name,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"信号对比报告已保存: {txt_path}\nJSON: {json_path}")
