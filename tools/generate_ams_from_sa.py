#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 SA 结果（bind 掩码级）生成 AMS 包装：
- 为每个 bind 生成一个包装模块 `bind_<dest_sanitized>.sv`
- 支持后端选择：ONN（默认）或 LUT（纯数字仿真）
- 生成汇接文件 `ams_top_bind_connect.sv`
注意：当前版本不解析 RTL 细节，仅以占位接口展示链路。
"""
import argparse
import json
from pathlib import Path
import re

TEMPLATE_BIND_ONN = """
// Auto-generated wrapper for bind: {dest}
module bind_{name} #(parameter int WIDTH = 8) (
  input  logic              clk,
  input  logic              rst_n,
  // 数字输入/输出（占位）：可按需求拆分为多个输入向量
  input  logic [WIDTH-1:0]  din,
  output logic [WIDTH-1:0]  dout
);
  // 占位：ADC/DAC 可根据真实上下文放置在更外层或内部；此处仅示例链路
  // 数字->实值->ONN->数字
  real r_in;
  ideal_dac #(.BITS(WIDTH), .VFS(1.0)) u_dac (
    .code (din),
    .vout (r_in)
  );

  logic [WIDTH-1:0] onn_out;
  onn_linear_block #(
    .PARAM_INPUTS (1),
    .PARAM_OUTPUTS(1),
    .PARAM_WIDTH  (WIDTH),
    .SCALE_W      (1.0)
  ) u_onn (
    .din_flat  (din),
    .dout_flat (onn_out)
  );

  // 实值->数字（此处将 ONN 数字直接输出；若 ONN 输出为 real，可改为 ideal_adc）
  assign dout = onn_out;
endmodule
"""

TEMPLATE_BIND_LUT = """
// Auto-generated wrapper for bind: {dest}
module bind_{name} #(parameter int WIDTH = 8) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic [WIDTH-1:0]  din,
  output logic [WIDTH-1:0]  dout
);
  // Pure-digital LUT backend for traditional simulators
  lut_block #(.WIDTH(WIDTH)) u_lut (
    .clk (clk),
    .rst_n (rst_n),
    .din (din),
    .dout(dout)
  );
endmodule
"""

TEMPLATE_CONNECT_TOP = """
// Auto-generated AMS bind connection top
module ams_top_bind_connect #(parameter int WIDTH=8) (
  input  logic clk,
  input  logic rst_n
);
  // 示例：为每个 bind 提供简单的占位信号
{wires}
{insts}
endmodule
"""

def sanitize(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def generate(sa_path: Path, out_dir: Path, backend: str = 'onn'):
    payload = json.loads(sa_path.read_text(encoding='utf-8'))
    binds = payload.get('binds', [])
    out_dir.mkdir(parents=True, exist_ok=True)

    wire_defs = []
    inst_defs = []

    for b in binds:
        dest = b.get('dest', 'unknown')
        name = sanitize(dest)
        sv_path = out_dir / f"bind_{name}.sv"
        if backend == 'lut':
            sv_path.write_text(TEMPLATE_BIND_LUT.format(dest=dest, name=name), encoding='utf-8')
        else:
            sv_path.write_text(TEMPLATE_BIND_ONN.format(dest=dest, name=name), encoding='utf-8')
        # 为连接顶层生成占位信号与实例
        wire_defs.append(f"  logic [7:0] din_{name};\n  logic [7:0] dout_{name};")
        inst_defs.append(
            f"  bind_{name} u_{name}(.clk(clk), .rst_n(rst_n), .din(din_{name}), .dout(dout_{name}));"
        )

    top = TEMPLATE_CONNECT_TOP.format(wires='\n'.join(wire_defs), insts='\n'.join(inst_defs))
    (out_dir / 'ams_top_bind_connect.sv').write_text(top, encoding='utf-8')
    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sa', type=str, required=True, help='SA best json path')
    ap.add_argument('--out', type=str, required=True, help='Output folder for generated SV')
    ap.add_argument('--top', type=str, default='', help='Optional: copy connect top to this path')
    ap.add_argument('--backend', type=str, default='onn', choices=['onn','lut'], help='Wrapper backend implementation')
    args = ap.parse_args()

    sa_path = Path(args.sa)
    out_dir = Path(args.out)
    if not sa_path.exists():
        raise SystemExit(f"SA json not found: {sa_path}")

    out = generate(sa_path, out_dir, backend=args.backend)
    print(f"[GEN] Generated AMS wrappers at: {out}")

    if args.top:
        top_path = Path(args.top)
        (out / 'ams_top_bind_connect.sv').replace(top_path)
        print(f"[GEN] Copied ams_top_bind_connect.sv to: {top_path}")

if __name__ == '__main__':
    main()
