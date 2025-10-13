#!/usr/bin/env python3
"""
基础可视化：从 DFG 文本中抽取 (Bind dest: X tree: ... (Terminal Y) ... )，
建立简单的信号依赖图并输出 DOT/HTML。

注意：
- 仅基于终端引用(Terminal)建立边：Y -> X。
- focus/depth/keep 参数当前做占位处理，后续可扩展为子图过滤。
"""
from __future__ import annotations
from pathlib import Path
import html
import re
from typing import Dict, List, Optional


TERMINAL_RE = re.compile(r"\(Terminal\s+([^\s\)]+)")
BIND_HEADER_RE = re.compile(r"\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)", re.DOTALL)


def _parse_binds(text: str) -> Dict[str, str]:
    binds: Dict[str, str] = {}
    for m in BIND_HEADER_RE.finditer(text):
        dest = m.group(1)
        expr = m.group(2).strip()
        binds[dest] = expr
    return binds


def _extract_terminals(expr: str) -> List[str]:
    return [m.group(1) for m in TERMINAL_RE.finditer(expr)]


def _to_dot(edges: List[tuple[str, str]], label: Optional[str] = None) -> str:
    lines = ["digraph DFG {", "  rankdir=LR;"]
    if label:
        lines.append(f"  labelloc=\"t\"; label=\"{html.escape(label)}\";")
    # Declare nodes implicitly by edges
    for src, dst in edges:
        lines.append(f"  \"{src}\" -> \"{dst}\";")
    lines.append("}")
    return "\n".join(lines)


def _to_html(binds: Dict[str, str], edges: List[tuple[str, str]], title: str) -> str:
    rows = []
    for dest, expr in binds.items():
        rows.append(f"<tr><td><code>{html.escape(dest)}</code></td><td><pre>{html.escape(expr)}</pre></td></tr>")
    body = f"""
<!DOCTYPE html>
<html lang=\"zh\"><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>
<style>body{{font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;}} pre{{white-space: pre-wrap;}} table{{border-collapse: collapse; width: 100%;}} td,th{{border:1px solid #ccc; padding:6px;}} th{{background:#f7f7f7;}}</style>
</head><body>
<h2>{html.escape(title)}</h2>
<p>Signals: {len(binds)} | Edges: {len(edges)}</p>
<table><thead><tr><th>dest</th><th>tree</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table>
</body></html>
"""
    return body


def visualize_from_dfg(dfg_file: str, output_dir: str, *, stem: Optional[str] = None,
                       focus: Optional[str] = None, depth: int = 2, keep: Optional[str] = None,
                       html: bool = True, dot: bool = True) -> Dict:
    p = Path(dfg_file)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = stem or p.stem

    text = p.read_text(encoding='utf-8', errors='ignore')
    binds = _parse_binds(text)

    # 构建边：Terminal -> dest
    edges: List[tuple[str, str]] = []
    for dest, expr in binds.items():
        for t in _extract_terminals(expr):
            edges.append((t, dest))

    title = f"DFG Visualization - {name}"
    out_files: Dict[str, str] = {}

    if dot:
        dot_str = _to_dot(edges, label=title)
        dot_path = out / f"{name}.dot"
        dot_path.write_text(dot_str, encoding='utf-8')
        out_files['dot'] = str(dot_path)

    if html:
        html_str = _to_html(binds, edges, title)
        html_path = out / f"{name}.html"
        html_path.write_text(html_str, encoding='utf-8')
        out_files['html'] = str(html_path)

    return {
        'files': out_files,
        'metrics': {
            'signals': len(binds),
            'edges': len(edges),
        }
    }
