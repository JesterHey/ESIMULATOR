#!/usr/bin/env python3
"""
自动化处理 4004 的 3 个模块（alu / instruction_decode / timing_io）：
  1) 使用 Pyverilog 的 example_dataflow_simplify.py 生成 DFG
  2) 调用本项目 CLI 运行 analyze（生成 *_linearity_graph.json 与 *_bind_masks.json 等）
  3) 可选 compare-signals（信号覆盖）
    4) 可选 visualize（DOT/HTML，并可用 graphviz 生成 PNG）

示例：
  python tools/auto_process_4004_modules.py \
    --pyverilog-example /Users/xuxiaolan/PycharmProjects/Pyverilog/examples/example_dataflow_simplify.py \
    --verilog-dir 4004_full_verilog --dfg-dir dfg_files --results-dir results \
    --modules alu,instruction_decode,timing_io --linearity-mode arith --visualize

注意：
  - 需要已安装 Pyverilog；并提供 Pyverilog 示例脚本路径。
  - Verilog 源应保存为 UTF-8，避免预处理阶段解码失败。
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict


def run(cmd: List[str], cwd: Path | None = None, stdout_to: Path | None = None) -> int:
    print('[RUN]', ' '.join(cmd))
    if stdout_to is not None:
        stdout_to.parent.mkdir(parents=True, exist_ok=True)
        with open(stdout_to, 'w', encoding='utf-8') as f:
            cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, stdout=f)
            return cp.returncode
    cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True)
    return cp.returncode


def ensure_file(p: Path, desc: str) -> None:
    if not p.exists():
        raise SystemExit(f'[ERR] 找不到{desc}: {p}')


def process_module(module: str, args) -> Dict:
    root = Path(__file__).resolve().parent.parent
    cli = root / 'esimulator_cli.py'
    ensure_file(cli, 'CLI 脚本 esimulator_cli.py')

    pyv = Path(args.pyverilog_example)
    ensure_file(pyv, 'Pyverilog 示例 example_dataflow_simplify.py')

    v_path = Path(args.verilog_dir) / f'{module}.v'
    ensure_file(v_path, f'Verilog 源 {module}.v')

    dfg_path = Path(args.dfg_dir) / f'{module}_dfg.txt'
    dfg_path.parent.mkdir(parents=True, exist_ok=True)

    out_dir = Path(args.results_dir) / (module + '_result')
    out_dir.mkdir(parents=True, exist_ok=True)

    # 0) （可选）将 Verilog 转为 UTF-8（就地备份 .bak 并覆盖），缓解 0xA9 等编码问题
    if getattr(args, 'recode_utf8', False):
        try:
            raw = v_path.read_bytes()
            try:
                txt = raw.decode('utf-8')
            except UnicodeDecodeError:
                for enc in ('cp1252', 'latin1', 'mac_roman'):
                    try:
                        txt = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise
            v_path_backup = v_path.with_suffix(v_path.suffix + '.bak')
            if not v_path_backup.exists():
                v_path_backup.write_bytes(raw)
            v_path.write_text(txt, encoding='utf-8')
            print(f"[INFO] 已将 {v_path} 规范为 UTF-8（原始备份: {v_path_backup.name}）")
        except Exception as e:
            print(f"[WARN] 重编码 {v_path} 失败: {e}")

    # 1) 用 Pyverilog 生成 DFG
    rc = run([sys.executable, str(pyv), '-t', module, str(v_path)], stdout_to=dfg_path)
    if rc != 0:
        return {
            'module': module,
            'verilog': str(v_path),
            'dfg': str(dfg_path),
            'output_dir': str(out_dir),
            'status': 'pyverilog_failed',
            'returncode': rc,
        }

    # 可选：只保留 Bind 行（当前分析器可直接解析混合输出，此步非必需）
    if args.only_binds:
        text = dfg_path.read_text(encoding='utf-8', errors='ignore').splitlines()
        binds = [ln for ln in text if ln.startswith('(Bind dest:')]
        dfg_path.write_text('\n'.join(binds) + ('\n' if binds else ''), encoding='utf-8')

    # 2) analyze
    prefix = (module + '.') if args.module_prefix_mode == 'auto' else ''
    rc1 = run([
        sys.executable, str(cli), 'analyze', str(dfg_path),
        '--output', str(out_dir),
        '--format', 'json',
        '--linearity-mode', args.linearity_mode,
        '--verilog-file', str(v_path),
        '--module-prefix', prefix,
    ])

    # 3) compare-signals（可选）
    rc2 = 0
    if not args.skip_compare:
        rc2 = run([
            sys.executable, str(cli), 'compare-signals', str(dfg_path),
            '--verilog-file', str(v_path),
            '--module-prefix', prefix,
            '--output', str(out_dir),
            '--linearity-mode', args.linearity_mode,
        ])

    # 4) visualize（可选）
    rc3 = 0
    if args.visualize:
        viz_dir = out_dir / 'viz'
        rc3 = run([
            sys.executable, str(cli), 'visualize', str(dfg_path),
            '--output', str(viz_dir),
        ])
        # 4.1) 使用 graphviz 渲染 PNG（可选）
        if args.render_png and rc3 == 0:
            dot_files = sorted(viz_dir.glob('*.dot'))
            rc_png = 0
            for df in dot_files:
                rc_png |= run(['dot', '-Tpng', str(df), '-O'])
            rc3 |= rc_png

    # 汇总 compare-signals 摘要
    sig_json = out_dir / f'{dfg_path.stem}_signal_compare.json'
    summary = {}
    if sig_json.exists():
        try:
            data = json.loads(sig_json.read_text(encoding='utf-8'))
            summary = data.get('summary', {})
        except Exception as e:
            summary = {'error': str(e)}

    return {
        'module': module,
        'verilog': str(v_path),
        'dfg': str(dfg_path),
        'output_dir': str(out_dir),
        'linearity_mode': args.linearity_mode,
        'status': 'ok' if rc1 == 0 and rc2 == 0 and rc3 == 0 else 'partial',
        'returncodes': {'analyze': rc1, 'compare': rc2, 'visualize': rc3},
        'compare_summary': summary,
    }


def main():
    ap = argparse.ArgumentParser(description='自动化处理 4004 模块（DFG 生成 + 分析 + 可视化）')
    ap.add_argument('--modules', default='alu,instruction_decode,timing_io', help='逗号分隔模块名（默认: alu,instruction_decode,timing_io）')
    ap.add_argument('--pyverilog-example', required=True, help='Pyverilog 示例脚本路径（example_dataflow_simplify.py）')
    ap.add_argument('--verilog-dir', default='4004_full_verilog', help='Verilog 源目录（默认 4004_full_verilog）')
    ap.add_argument('--dfg-dir', default='dfg_files', help='DFG 输出目录（默认 dfg_files）')
    ap.add_argument('--results-dir', default='results', help='结果输出根目录（默认 results）')
    ap.add_argument('--linearity-mode', choices=['arith', 'gf2'], default='arith', help='线性判定模式（默认 arith）')
    ap.add_argument('--module-prefix-mode', choices=['auto', 'none'], default='auto', help='auto: 使用 <module>. 作为前缀；none: 空前缀')
    ap.add_argument('--only-binds', action='store_true', help='将 DFG 输出过滤为仅包含 Bind 行')
    ap.add_argument('--skip-compare', action='store_true', help='跳过 compare-signals 阶段')
    ap.add_argument('--visualize', action='store_true', help='生成 DOT/HTML 可视化')
    ap.add_argument('--render-png', action='store_true', help='在 visualize 基础上用 graphviz 将 DOT 渲染为 PNG')
    ap.add_argument('--recode-utf8', action='store_true', help='在调用 Pyverilog 前尝试将 Verilog 源重编码为 UTF-8（生成 .bak 备份）')
    args = ap.parse_args()

    modules = [m.strip() for m in args.modules.split(',') if m.strip()]
    results: List[Dict] = []
    for m in modules:
        print(f'\n===== 处理模块: {m} =====')
        try:
            info = process_module(m, args)
        except Exception as e:
            info = {
                'module': m,
                'status': 'exception',
                'error': str(e),
            }
        results.append(info)

    # 汇总
    root_out = Path(args.results_dir)
    root_out.mkdir(parents=True, exist_ok=True)
    overall = root_out / 'overall_summary.json'
    overall.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n[OK] 汇总已写入: {overall}')
    print('简表:')
    for r in results:
        st = r.get('status')
        summ = r.get('compare_summary', {})
        out_dir = r.get('output_dir', '-')
        module_name = r.get('module', '-')
        print(f"  - {module_name}: status={st} out={out_dir} total={summ.get('total_names','-')} verilog={summ.get('verilog_signals','-')} binds={summ.get('bind_count','-')}")


if __name__ == '__main__':
    main()
