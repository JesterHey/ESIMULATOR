#!/usr/bin/env python3
"""
一个简单的 Verilog 文件解析器，用于提取信号定义所在的行号。
"""
from __future__ import annotations
import re
from typing import Dict

def parse_verilog_for_line_numbers(file_path: str, module_prefix: str = "") -> Dict[str, int]:
    """
    解析 Verilog 文件，提取信号名及其首次出现的行号。

    Args:
        file_path: Verilog 文件路径。
        module_prefix: 可选的模块名前缀，用于构建完整的信号名 (e.g., "alu.")。

    Returns:
        一个字典，映射信号名到行号。
    """
    line_map: Dict[str, int] = {}
    # 正则表达式匹配 input, output, reg, wire, assign 的目标信号
    # 支持向量 [msb:lsb] 和多信号声明
    patterns = [
        # input/output/reg/wire [signed] [range] signal1, signal2, ...;
        re.compile(r"^\s*(?:input|output|reg|wire)\s*(?:signed\s*)?(?:\[[^\]]+\]\s*)?((?:\w+\s*,?\s*)+);"),
        # assign signal = ...;
        re.compile(r"^\s*assign\s+(\w+)\s*="),
    ]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # 跳过注释
                line = line.split('//')[0].strip()
                if not line:
                    continue

                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        # 对于声明语句，可能有多个信号
                        if ',' in match.group(1):
                            signals = [s.strip() for s in match.group(1).split(',') if s.strip()]
                            for sig in signals:
                                full_name = f"{module_prefix}{sig}" if module_prefix else sig
                                if full_name not in line_map:
                                    line_map[full_name] = line_num
                        else:
                            # assign 或单信号声明
                            sig = match.group(1).strip()
                            full_name = f"{module_prefix}{sig}" if module_prefix else sig
                            if full_name not in line_map:
                                line_map[full_name] = line_num
                        # 一行只匹配一种模式
                        break
    except FileNotFoundError:
        print(f"[VerilogParser] 警告: Verilog 文件未找到 at {file_path}")
        return {}
    except Exception as e:
        print(f"[VerilogParser] 解析时发生错误 {file_path}: {e}")
        return {}

    return line_map

if __name__ == '__main__':
    # 演示
    import sys
    if len(sys.argv) > 1:
        v_file = sys.argv[1]
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        locations = parse_verilog_for_line_numbers(v_file, prefix)
        import json
        print(json.dumps(locations, indent=2))
    else:
        print("用法: python -m esimulator.utils.verilog_parser <verilog_file_path> [module_prefix]")
