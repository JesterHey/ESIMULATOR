#!/usr/bin/env python3
"""SA 命令：从 DFG -> 导出 bind masks -> 跑 Bind 掩码 SA -> 输出最优 JSON"""
from __future__ import annotations
import os
import sys
from typing import Any


def run_sa(args: Any) -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    from esimulator.core.report_generator import ReportGenerator
    from src.simulated_annealing import run_bindmask_anneal, BindCostWeights
    import os.path as _op

    dfg_file = args.dfg_file
    out_dir = getattr(args, 'output', 'results')
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(dfg_file):
        print(f"错误: 找不到DFG文件 {dfg_file}")
        return

    stem = _op.splitext(_op.basename(dfg_file))[0]
    bind_json = _op.join(out_dir, f"{stem}_bind_masks.json")
    graph_json = _op.join(out_dir, f"{stem}_linearity_graph.json")

    # 若缺少导出，则先分析并导出
    need_analyze = not (os.path.exists(bind_json) and os.path.exists(graph_json))
    if need_analyze:
        print("[SA] 缺少导出，先运行 analyze 并生成 graph/bind …")
        analyzer = LinearityAnalyzer()
        report = analyzer.analyze_dfg_file(dfg_file)
        rg = ReportGenerator(out_dir)
        # 附加操作符线性标签（尽力而为，不阻止流程）
        try:
            from src.analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer
            _operator_tags = {op: 1 for op in CorrectedLinearityAnalyzer(linearity_mode=getattr(args, 'linearity_mode', 'arith')).linear_operators}
        except Exception:
            _operator_tags = None
        rg.generate_text_report(report, "linearity_analysis.txt")
        rg.generate_json_report(report, "linearity_analysis.json", operator_linearity_tags=_operator_tags)
        rg.generate_graph_json(report, dfg_file, f"{stem}_linearity_graph.json")
        rg.generate_bind_masks_json(
            report,
            dfg_file,
            f"{stem}_bind_masks.json",
            linearity_mode=getattr(args, 'linearity_mode', 'arith'),
            omit_trivial=getattr(args, 'omit_trivial', False),
            include_human_labels=True,
        )
        print(f"[SA] 导出完成: {graph_json}, {bind_json}")
    else:
        print(f"[SA] 复用已存在导出: {graph_json}, {bind_json}")

    # 读取权重参数（使用默认或命令行覆盖）
    w = BindCostWeights(
        wi=getattr(args, 'wi', 0.7),
        wz=getattr(args, 'wz', 1.3),
        w3=getattr(args, 'w3', 0.3),
        wa=getattr(args, 'wa', 1.4),
        area_a1=getattr(args, 'area_a1', 0.6),
        area_a2=getattr(args, 'area_a2', 1.2),
        delay_d1=getattr(args, 'delay_d1', 1.2),
        power_p1=getattr(args, 'power_p1', 0.3),
        iface_i1=getattr(args, 'iface_i1', 0.8),
    )

    export_path = _op.join(out_dir, f"{stem}_bindmask_sa_best.json")
    path = run_bindmask_anneal(
        bind_json,
        w,
        initial_temperature=getattr(args, 'ti', 40.0),
        final_temperature=getattr(args, 'tf', 0.5),
        cooling_rate=getattr(args, 'cr', 0.92),
        iterations_per_temp=getattr(args, 'iters', 40),
        max_iterations=getattr(args, 'maxit', 2500),
        multi_start_runs=getattr(args, 'runs', 3),
        seed=getattr(args, 'seed', 42),
        export_path=export_path,
    )
    if path:
        print(f"[SA] 完成: {path}")
    else:
        print("[SA] 未能生成结果文件")

__all__ = ["run_sa"]
