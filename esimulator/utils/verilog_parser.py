#!/usr/bin/env python3
"""
一个简单的 Verilog 文件解析器，用于提取信号定义所在的行号。
"""
from __future__ import annotations
import re
from typing import Dict, List

def _split_commas_outside_braces(s: str) -> List[str]:
    """按逗号分割，但忽略花括号/圆括号/方括号内的逗号。"""
    parts: List[str] = []
    depth_brace = depth_paren = depth_brack = 0
    start = 0
    for i, ch in enumerate(s):
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace = max(0, depth_brace - 1)
        elif ch == '(':
            depth_paren += 1
        elif ch == ')':
            depth_paren = max(0, depth_paren - 1)
        elif ch == '[':
            depth_brack += 1
        elif ch == ']':
            depth_brack = max(0, depth_brack - 1)
        elif ch == ',' and depth_brace == 0 and depth_paren == 0 and depth_brack == 0:
            parts.append(s[start:i])
            start = i + 1
    tail = s[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _sanitize_identifier(token: str) -> str:
    """提取合法的 Verilog 标识符前缀（去掉数组/切片/多余符号）。"""
    token = token.strip()
    # 去掉左侧类型限定、range 等
    # 仅提取以字母或下划线开头的标识符
    m = re.match(r"^[A-Za-z_][A-Za-z0-9_$]*", token)
    return m.group(0) if m else ""

def _strip_leading_type_keywords(s: str) -> str:
    """移除名称左侧可能出现的类型关键字（reg/wire/signed）。"""
    s = s.lstrip()
    while True:
        m = re.match(r"^(?:reg|wire|signed)\b\s*", s, flags=re.IGNORECASE)
        if not m:
            break
        s = s[m.end():]
    return s.lstrip()


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
    # 支持向量 [msb:lsb] 和多信号声明（含多行）
    decl_pattern_single = re.compile(r"^\s*(?:input|output|reg|wire)\s*(?:signed\s*)?(?:\[[^\]]+\]\s*)?([^;]+);", re.IGNORECASE)
    decl_header_pattern = re.compile(r"^\s*(?:input|output|reg|wire)\b", re.IGNORECASE)
    decl_payload_pattern = re.compile(r"^\s*(?:input|output|reg|wire)\s*(?:signed\s*)?(?:\[[^\]]+\]\s*)?(.+?)\s*;\s*$", re.IGNORECASE)
    assign_pattern = re.compile(r"^\s*assign\s+(\w+)\s*=", re.IGNORECASE)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            in_decl = False
            decl_buf = ""
            decl_start_line = 0

            for line_num, raw in enumerate(f, 1):
                # 跳过注释
                line = raw.split('//')[0].strip()
                if not line:
                    continue

                if in_decl:
                    decl_buf += " " + line
                    if ';' in line:
                        # 结束多行声明
                        m = decl_payload_pattern.search(decl_buf)
                        if m:
                            names_payload = m.group(1)
                            chunks = _split_commas_outside_braces(names_payload)
                            for chunk in chunks:
                                left = chunk.split('=')[0]
                                left = _strip_leading_type_keywords(left)
                                name = _sanitize_identifier(left)
                                if not name:
                                    continue
                                full_name = f"{module_prefix}{name}" if module_prefix else name
                                if full_name not in line_map:
                                    line_map[full_name] = decl_start_line
                        # 重置
                        in_decl = False
                        decl_buf = ""
                        decl_start_line = 0
                    continue

                # 尝试单行声明
                decl_match = decl_pattern_single.search(line)
                if decl_match:
                    names_payload = decl_match.group(1)
                    chunks = _split_commas_outside_braces(names_payload)
                    for chunk in chunks:
                        left = chunk.split('=')[0]
                        left = _strip_leading_type_keywords(left)
                        name = _sanitize_identifier(left)
                        if not name:
                            continue
                        full_name = f"{module_prefix}{name}" if module_prefix else name
                        if full_name not in line_map:
                            line_map[full_name] = line_num
                    continue

                # 多行声明起始（无分号）
                if decl_header_pattern.search(line) and ';' not in line:
                    in_decl = True
                    decl_buf = line
                    decl_start_line = line_num
                    continue

                assign_match = assign_pattern.search(line)
                if assign_match:
                    sig = assign_match.group(1).strip()
                    full_name = f"{module_prefix}{sig}" if module_prefix else sig
                    if full_name not in line_map:
                        line_map[full_name] = line_num
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
