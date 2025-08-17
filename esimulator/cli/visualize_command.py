#!/usr/bin/env python3
"""可视化命令

更新: 使用 `esimulator.visual` 模块生成 DOT / HTML 输出。
"""

import os
import sys
from typing import Any

def run_visualize(args: Any) -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from esimulator.visual import visualize_from_dfg

    if not os.path.exists(args.dfg_file):
        print(f"错误: 找不到DFG文件 {args.dfg_file}")
        return

    out_dir = args.output
    os.makedirs(out_dir, exist_ok=True)

    print(f"生成可视化 (DOT/HTML): {args.dfg_file}")
    print("=" * 50)

    try:
        res = visualize_from_dfg(
            args.dfg_file,
            out_dir,
            stem=None,
            focus=getattr(args, 'focus', None),
            depth=getattr(args, 'depth', 2),
            keep=getattr(args, 'filter', None),
            html=True,
            dot=True,
            split_subgraphs=getattr(args, 'split_subgraphs', False)
        )
        print(f"已输出: {out_dir}")
        print("指标: ", res['metrics'])
        print("提示: 使用 graphviz 可将 dot 转为 png: dot -Tpng <file>.dot -o <file>.png")
    except Exception as e:
        print(f"可视化过程中出错: {e}")
        sys.exit(1)
