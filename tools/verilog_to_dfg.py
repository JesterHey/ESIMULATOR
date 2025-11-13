#!/usr/bin/env python3
"""
verilog_to_dfg.py
=================
将单个 Verilog 模块中的“组合逻辑”提取为本项目使用的 DFG 文本格式，便于后续
CorrectedLinearityAnalyzer 做线性标注与行号映射。

一、核心思路
-------------
1. 解析 Verilog AST（依赖 Pyverilog）
2. 仅收集下列来源形成 Bind：
   - 连续赋值 assign 语句 (Assign)
   - 组合 always 块 (always @* / always_comb / 敏感列表中仅包含信号、无 posedge/negedge)
     * 对其中的阻塞赋值 (=) 视为组合绑定
3. 顺序 always 块 (posedge/negedge) 默认跳过（可选开关包含其 RHS 作为组合表达式）
4. 每个绑定输出格式：
   (Bind dest:<信号名> tree:<表达式S表达式>)
   其中表达式递归使用以下节点：
     (Operator <OP_NAME> Next: <child> [, <child> ...])
     (Terminal <SIGNAL>)
     (IntConst <CONST>) / (IntCon <CONST>)
     (Concat Next: <child>, <child>, ...)
     (Partselect Var:(<子表达式>) MSB:(<子表达式>) LSB:(<子表达式>))
     (Branch Cond:(<子表达式>) True:(<子表达式>) False:(<子表达式>))  # 用于条件运算符 (?:)

二、限制 / TODO
----------------
- 未做层次展开（module 实例化不 inline）。若 DFG 需跨层次，请先用上游工具展开。
- case 语句暂未转换为 Branch 列表；初版仅支持三元运算符 (?:)。可后续扩展。
- 顺序 always 中的非阻塞赋值 (<=) 跳过；若希望包含其 RHS 可加 --include-seq-rhs
- generate/宏/参数求值未深度处理；Pyverilog 预处理需保证可解析。

三、使用示例
-------------
  pip install pyverilog
  python tools/verilog_to_dfg.py \
     --verilog 4004_full_verilog/alu.v \
     --module alu \
     --out dfg_files/alu_dfg.txt \
     --prefix alu.

多模块批量：
  for m in alu instruction_decode instruction_pointer scratchpad timing_io; do \
      python tools/verilog_to_dfg.py --verilog 4004_full_verilog/$m.v --module $m \
        --out dfg_files/${m}_dfg.txt --prefix $m.; \
  done

然后运行：
  python tools/analyze_4004_modules.py --modules alu,instruction_decode,...

四、表达式 -> S 表达式映射
----------------------------
Pyverilog AST 节点与本工具输出 OP_NAME 对应：
  +: Plus  -: Minus  *: Times  /: Divide  %: Mod
  <<: Sll  >>: Srl
  &: And  |: Or  ^: Xor  ~^ / ^~: Xnor
  ==: Eq  !=: NotEq  <: Lt  <=: Lte  >: Gt  >=: Gte
  一元 ~: Unot   +: Uplus   -: UnaryMinus  &: Uand  |: Unor  ^: Uxor

五、输出结构
-------------
DFG 文件为若干 (Bind ...) 片段，分析器按正则批量读取。

"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import List, Optional

# Pyverilog imports
try:
    from pyverilog.vparser.parser import parse
    from pyverilog.vparser.ast import (
        ModuleDef, Assign, Lvalue, Rvalue, Identifier, IntConst, Pointer, Partselect,
        Cond, UnaryOperator, Operator, Concat, BlockingSubstitution, NonblockingSubstitution,
        Always, SensList, Sens, Decl, InstanceList, Instance
    )
except ImportError:  # noqa: F401
    # 未安装 pyverilog：parse 置空；执行 main() 时直接退出即可。
    parse = None  # type: ignore

BINARY_OP_MAP = {
    '+': 'Plus', '-': 'Minus', '*': 'Times', '/': 'Divide', '%': 'Mod',
    '<<': 'Sll', '>>': 'Srl',
    '&&': 'And', '||': 'Or', '&': 'And', '|': 'Or', '^': 'Xor', '~^': 'Xnor', '^~': 'Xnor',
    '==': 'Eq', '!=': 'NotEq', '<': 'Lt', '<=': 'Lte', '>': 'Gt', '>=': 'Gte'
}
UNARY_OP_MAP = {
    '~': 'Unot', '+': 'Uplus', '-': 'UnaryMinus', '&': 'Uand', '|': 'Unor', '^': 'Uxor'
}


def is_comb_always(node) -> bool:
    """判断 always 是否为组合逻辑 (@* 或敏感列表全为电平，无 posedge/negedge)。"""
    sens = getattr(node, 'sens_list', None)
    if sens is None:
        return True  # always @* 在 Pyverilog 中 sens_list 可能为 None
    for s in getattr(sens, 'list', []):  # sens.list 可能不存在
        if getattr(s, 'type', None) in ('posedge', 'negedge'):
            return False
    return True


def expr_to_sexpr(node) -> str:
    """递归将 Pyverilog 表达式节点转换为项目使用的 S-expression 字符串。"""
    from pyverilog.vparser import ast as vast if parse else None  # type: ignore
    IdentifierT = getattr(vast, 'Identifier', tuple()) if vast else tuple()
    IntConstT = getattr(vast, 'IntConst', tuple()) if vast else tuple()
    PointerT = getattr(vast, 'Pointer', tuple()) if vast else tuple()
    PartselectT = getattr(vast, 'Partselect', tuple()) if vast else tuple()
    CondT = getattr(vast, 'Cond', tuple()) if vast else tuple()
    UnaryOpT = getattr(vast, 'UnaryOperator', tuple()) if vast else tuple()
    OperatorT = getattr(vast, 'Operator', tuple()) if vast else tuple()
    ConcatT = getattr(vast, 'Concat', tuple()) if vast else tuple()
    if isinstance(node, IdentifierT):
        return f"(Terminal {node.name})"
    if isinstance(node, IntConstT):
        return f"(IntConst {node.value})"
    if isinstance(node, PointerT):  # bit select a[i]
        base = expr_to_sexpr(node.var)
        msb = expr_to_sexpr(node.ptr)
        return f"(Partselect Var:{base} MSB:{msb} LSB:{msb})"
    if isinstance(node, PartselectT):  # a[msb:lsb]
        base = expr_to_sexpr(node.var)
        msb = expr_to_sexpr(node.msb)
        lsb = expr_to_sexpr(node.lsb)
        return f"(Partselect Var:{base} MSB:{msb} LSB:{lsb})"
    if isinstance(node, CondT):  # cond ? true : false
        c = expr_to_sexpr(node.cond)
        t = expr_to_sexpr(node.true_value)
        f = expr_to_sexpr(node.false_value)
        return f"(Branch Cond:{c} True:{t} False:{f})"
    if isinstance(node, UnaryOpT):
        op = UNARY_OP_MAP.get(node.__dict__.get('operator', ''), node.__dict__.get('operator', 'Unary'))
        child = expr_to_sexpr(node.children()[0])
        return f"(Operator {op} Next: {child})"
    if isinstance(node, OperatorT):  # binary or multi? children list
        ch = list(node.children())
        op_symbol = node.__dict__.get('operator', '')
        op_name = BINARY_OP_MAP.get(op_symbol, op_symbol or 'Op')
        # 链式 (a + b + c) 会被 Pyverilog 解析为左结合嵌套；我们保持嵌套形式
        sexprs = ', '.join(expr_to_sexpr(c) for c in ch)
        return f"(Operator {op_name} Next: {sexprs})"
    if isinstance(node, ConcatT):
        elems = ', '.join(expr_to_sexpr(c) for c in node.list)
        return f"(Concat Next: {elems})"
    # 兜底：字符串化
    return f"(Terminal {str(node)})"


def collect_assigns_from_always(item, binds, prefix: str, include_seq_rhs: bool):
    """收集 always 块内的阻塞赋值 (=) 作为组合绑定；可选包含顺序块的 RHS。"""
    from pyverilog.vparser.ast import Block, IfStatement, CaseStatement

    from pyverilog.vparser import ast as vast if parse else None  # type: ignore
    BlockingT = getattr(vast, 'BlockingSubstitution', tuple()) if vast else tuple()
    NonblockingT = getattr(vast, 'NonblockingSubstitution', tuple()) if vast else tuple()
    IdentifierT = getattr(vast, 'Identifier', tuple()) if vast else tuple()
    BlockT = getattr(vast, 'Block', tuple()) if vast else tuple()
    IfT = getattr(vast, 'IfStatement', tuple()) if vast else tuple()
    CaseT = getattr(vast, 'CaseStatement', tuple()) if vast else tuple()

    def walk(stmt):
        if stmt is None:
            return
        # 阻塞赋值 -> 组合；非阻塞依配置
        if isinstance(stmt, BlockingT):
            l, r = stmt.left, stmt.right
            if isinstance(l, IdentifierT):
                binds.append((prefix + l.name, r))
        elif isinstance(stmt, NonblockingT):
            if not include_seq_rhs:
                return
            l, r = stmt.left, stmt.right
            if isinstance(l, IdentifierT):
                binds.append((prefix + l.name, r))
        elif isinstance(stmt, BlockT):
            for s in stmt.statements:
                walk(s)
        elif isinstance(stmt, IfT):
            # 仅提取条件表达式中出现的赋值 (true_stmt, false_stmt)
            walk(stmt.true_statement)
            walk(stmt.false_statement)
        elif isinstance(stmt, CaseT):
            # TODO: 可展开为多路 Branch；当前只遍历分支体内赋值
            for cc in stmt.caselist:
                for ss in cc.statement.statements if hasattr(cc.statement, 'statements') else [cc.statement]:
                    walk(ss)
        else:
            # 其他语句类型（For/While 等）暂不支持
            pass
    walk(item.statement)


def extract_module(verilog_file: Path, module_name: str, prefix: str, include_seq_rhs: bool) -> List[str]:
    ast, _ = parse([str(verilog_file)])
    description = ast.description
    from pyverilog.vparser import ast as vast  # type: ignore
    ModuleDefT = getattr(vast, 'ModuleDef', tuple())
    AssignT = getattr(vast, 'Assign', tuple())
    IdentifierT = getattr(vast, 'Identifier', tuple())
    AlwaysT = getattr(vast, 'Always', tuple())
    modules = [d for d in description.definitions if isinstance(d, ModuleDefT)]
    target = None
    for m in modules:
        if m.name == module_name:
            target = m
            break
    if not target:
        raise SystemExit(f"未找到模块 {module_name} 于 {verilog_file}")

    binds = []  # (dest, expr_node)

    for item in target.items:
        # 连续赋值
        if isinstance(item, AssignT):
            l = item.left
            r = item.right
            if isinstance(l, IdentifierT):
                binds.append((prefix + l.name, r))
        # always 块（组合）
        elif isinstance(item, AlwaysT) and is_comb_always(item):
            collect_assigns_from_always(item.statement if hasattr(item, 'statement') else item, binds, prefix, include_seq_rhs)
        # 顺序 always：按需提取非阻塞 RHS（需要 include_seq_rhs=True）
        elif isinstance(item, AlwaysT) and include_seq_rhs:
            collect_assigns_from_always(item.statement if hasattr(item, 'statement') else item, binds, prefix, include_seq_rhs)
        else:
            continue

    # 转换为 (Bind ...) 文本
    out_lines: List[str] = []
    for dest, expr_ast in binds:
        sexpr = expr_to_sexpr(expr_ast)
        out_lines.append(f"(Bind dest:{dest} tree:{sexpr})")
    return out_lines


def main():
    ap = argparse.ArgumentParser(description='从 Verilog 模块抽取组合逻辑生成 DFG')
    ap.add_argument('--verilog', required=True, help='Verilog 源文件')
    ap.add_argument('--module', required=True, help='模块名')
    ap.add_argument('--out', required=True, help='输出 DFG 文件路径')
    ap.add_argument('--prefix', default='', help='为生成的 dest/sources 添加前缀 (如 alu.)')
    ap.add_argument('--include-seq-rhs', action='store_true', help='包含顺序 always (posedge) 中的非阻塞赋值 RHS 作为绑定')
    args = ap.parse_args()

    if parse is None:
        raise SystemExit('缺少 pyverilog，请先: pip install pyverilog')

    verilog_path = Path(args.verilog)
    if not verilog_path.exists():
        raise SystemExit(f'Verilog 文件不存在: {verilog_path}')

    lines = extract_module(verilog_path, args.module, args.prefix, args.include_seq_rhs)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'生成 DFG: {args.out} (共 {len(lines)} 条 Bind)')


if __name__ == '__main__':
    main()
