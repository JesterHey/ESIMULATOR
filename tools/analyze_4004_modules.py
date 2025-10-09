#!/usr/bin/env python3
"""批量分析 4004 各子模块的 DFG 线性标注与信号覆盖。

使用约定：
  - DFG 文件命名: dfg_files/<module>_dfg.txt （需由上游 Pyverilog/DFG 提取流程生成）
  - Verilog 源文件: 4004_full_verilog/<module>.v
  - module_prefix: <module>.  （可根据你的 DFG 命名风格调整，若 DFG 中未加前缀可传空字符串）

示例：
  python tools/analyze_4004_modules.py \
      --modules alu,instruction_decode,instruction_pointer,scratchpad,timing_io \
      --out results --linearity-mode arith

脚本执行：
  1. 对每个模块调用 analyze（生成 *_linearity_graph.json 与 *_bind_masks.json 等）
  2. 调用 compare-signals 生成信号覆盖报告（需要 Verilog 源以提供行号）
  3. 汇总一个 overall_summary.json 便于快速查看各模块统计对比
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parent.parent
DFG_DIR = ROOT / 'dfg_files'
VERILOG_DIR = ROOT / '4004_full_verilog'
CLI = ROOT / 'esimulator_cli.py'


def run(cmd: List[str]):
    print('[RUN]', ' '.join(cmd))
    completed = subprocess.run(cmd, text=True)
    if completed.returncode != 0:
        print(f'[WARN] 命令非 0 退出: {completed.returncode}')


def analyze_module(module: str, args) -> Dict:
    dfg_path = DFG_DIR / f'{module}_dfg.txt'
    v_path = VERILOG_DIR / f'{module}.v'

    exists = dfg_path.exists() and v_path.exists()
    if not exists:
        return {
            'module': module,
            'dfg_exists': dfg_path.exists(),
            'verilog_exists': v_path.exists(),
            'skipped': True
        }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    module_prefix = module + '.' if not args.no_prefix else ''

    # 1) analyze
    run([
        'python', str(CLI), 'analyze', str(dfg_path),
        '--output', str(out_dir),
        '--linearity-mode', args.linearity_mode,
        '--verilog-file', str(v_path),
        '--module-prefix', module_prefix,
    ])

    # 2) compare-signals
    run([
        'python', str(CLI), 'compare-signals', str(dfg_path),
        '--verilog-file', str(v_path),
        '--module-prefix', module_prefix,
        '--output', str(out_dir),
        '--linearity-mode', args.linearity_mode,
    ])

    # 3) 摘取 compare-signals JSON 汇总
    stem = dfg_path.stem  # <module>_dfg
    sig_json = out_dir / f'{stem}_signal_compare.json'
    summary = {}
    if sig_json.exists():
        try:
            data = json.loads(sig_json.read_text(encoding='utf-8'))
            summary = data.get('summary', {})
        except Exception as e:
            summary = {'error': str(e)}

    return {
        'module': module,
        'dfg_file': str(dfg_path),
        'verilog_file': str(v_path),
        'linearity_mode': args.linearity_mode,
        'summary': summary,
        'skipped': False
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modules', default='alu,instruction_decode,instruction_pointer,scratchpad,timing_io',
                    help='逗号分隔的模块名列表 (默认: 4004 五大核心板)')
    ap.add_argument('--out', default='results', help='输出目录 (默认 results)')
    ap.add_argument('--linearity-mode', choices=['arith', 'gf2'], default='arith')
    ap.add_argument('--no-prefix', action='store_true', help='DFG 中信号未加模块名前缀时使用')
    args = ap.parse_args()

    modules = [m.strip() for m in args.modules.split(',') if m.strip()]

    overall: List[Dict] = []
    for mod in modules:
        print(f'\n===== 分析模块: {mod} =====')
        info = analyze_module(mod, args)
        overall.append(info)

    overall_path = Path(args.out) / 'overall_summary.json'
    overall_path.write_text(json.dumps(overall, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n汇总已写入: {overall_path}')

    # 终端简表
    print('\n模块结果摘要:')
    for item in overall:
        if item.get('skipped'):
            print(f"  - {item['module']}: 跳过 (DFG:{item.get('dfg_exists')} Verilog:{item.get('verilog_exists')})")
            continue
        summ = item.get('summary', {})
        print(f"  - {item['module']}: total={summ.get('total_names','?')} verilog={summ.get('verilog_signals','?')} binds={summ.get('bind_count','?')} missing_dest={len(summ.get('missing_line_for_bind_dests',[])) if 'missing_line_for_bind_dests' in summ else '?'} incomplete_src={len(summ.get('bind_with_incomplete_source_locations',[])) if 'bind_with_incomplete_source_locations' in summ else '?'}")

if __name__ == '__main__':
    main()
