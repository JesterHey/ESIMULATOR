#!/usr/bin/env python3
"""
线性分析命令
"""

import os
import sys
from typing import Any

def run_analyze(args: Any) -> None:
    """执行DFG线性分析"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from esimulator.core.linearity_analyzer import LinearityAnalyzer
    from esimulator.core.report_generator import ReportGenerator
    # 可选：增强版操作符线性标签（用于 JSON 报告元数据）
    try:
        from src.analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer
        _operator_tags = {op: 1 for op in CorrectedLinearityAnalyzer().linear_operators}
    except Exception:
        _operator_tags = None
    import os.path as _op
    
    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到DFG文件 {args.dfg_file}")
        return
    
    print(f"正在分析DFG文件: {args.dfg_file}")
    print("=" * 50)
    
    # 执行分析
    analyzer = LinearityAnalyzer()
    try:
        result = analyzer.analyze_dfg_file(args.dfg_file)

        report_gen = ReportGenerator(args.output)

        if args.format in ['txt', 'both']:
            txt_file = report_gen.generate_text_report(result, "linearity_analysis.txt")
            print(f"文本报告已保存到: {txt_file}")

        if args.format in ['json', 'both']:
            json_file = report_gen.generate_json_report(result, "linearity_analysis.json", operator_linearity_tags=_operator_tags)
            print(f"JSON报告已保存到: {json_file}")

        # 生成 SA 所需的图与 Bind 掩码 JSON
        stem = _op.splitext(_op.basename(args.dfg_file))[0]
        graph_name = f"{stem}_linearity_graph.json"
        bind_name = f"{stem}_bind_masks.json"
        graph_file = report_gen.generate_graph_json(result, args.dfg_file, graph_name)
        bind_file = report_gen.generate_bind_masks_json(
            result,
            args.dfg_file,
            bind_name,
            linearity_mode=getattr(args, 'linearity_mode', 'arith'),
            omit_trivial=getattr(args, 'omit_trivial', False),
            include_human_labels=True,
            verilog_file=args.verilog_file if args.verilog_file else "",
            module_prefix=args.module_prefix if hasattr(args, 'module_prefix') else '',
        )
        print(f"图/掩码已保存到: {graph_file}, {bind_file}")

        print("\n" + report_gen.generate_summary_report(result))

    except Exception as e:
        print(f"分析过程中出错: {e}")
        sys.exit(1)
