#!/usr/bin/env python3

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Union
import json
from pathlib import Path

try:
    import networkx as nx  # 可选：用于直接构建图供模拟退火使用
except ImportError:  # 允许在未安装 networkx 时继续运行文本分析
    nx = None  # type: ignore

@dataclass
class ExpressionNode:
    """表达式树节点"""
    node_type: str  # 'operator', 'terminal', 'constant', 'branch', 'concat', 'partselect', 'unknown'
    value: str      # 运算符名称、终端名称等
    children: List['ExpressionNode']
    is_linear: Optional[bool] = None
    position: Optional[int] = None  # 在原始表达式中的位置
    
    def __str__(self, depth=0):
        indent = "  " * depth
        if self.node_type == 'operator':
            result = f"{indent}{self.value} ({self.node_type})\n"
            for child in self.children:
                result += child.__str__(depth + 1)
            return result
        else:
            return f"{indent}{self.value} ({self.node_type})\n"

class ParseError(Exception):
    pass

def _skip_ws(s: str, i: int) -> int:
    """跳过空白字符，返回新索引"""
    while i < len(s) and s[i].isspace():
        i += 1
    return i

def _read_token(s: str, i: int, stop_chars: str = "():, \n\t") -> Tuple[str, int]:
    """读取 token，直到遇到指定停止字符"""
    start = i
    while i < len(s) and s[i] not in stop_chars:
        i += 1
    if start == i:
        raise ParseError(f"期待 token 于位置 {i}")
    return s[start:i], i

def _extract_parenthesized(s: str, i: int) -> Tuple[str, int]:
    """从索引 i 开始，提取完整的括号内容，返回该子串及下一个索引位置"""
    if s[i] != '(':
        raise ParseError(f"位置 {i} 不是 '('")
    depth = 0
    start = i
    while i < len(s):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return s[start:i+1], i+1
        i += 1
    raise ParseError(f"括号未闭合，起点 {start}")

def parse_expression(s: str, i: int = 0) -> Tuple[ExpressionNode, int]:
    """
    递归解析表达式文本，返回 ExpressionNode 对象及新索引位置
    支持 Terminal, IntConst/IntCon, Operator, Concat, Branch, Partselect 等简单规则  
    """
    i = _skip_ws(s, i)
    if i >= len(s):
        # 空表达式直接返回 unknown
        return ExpressionNode("unknown", "", [], position=i), i
    if s[i] != '(': 
        # 裸值直接识别为 constant 或 terminal
        val = s[i:].strip()
        # 数字、Verilog常量、数组下标、4'b0000等
        if val.isdigit() or val.startswith("'") or val.replace('.', '', 1).isdigit() or ("'" in val and 'b' in val):
            return ExpressionNode("constant", val, [], position=i), len(s)
        else:
            return ExpressionNode("terminal", val, [], position=i), len(s)
    # 读取关键字：识别节点类型
    j = i + 1
    j = _skip_ws(s, j)
    key, j = _read_token(s, j)
    key = key.strip()
    # Terminal 和常量直接采用括号内全部内容处理
    if key.startswith("Terminal") or key.startswith("IntCon") or key.startswith("IntConst"):
        whole, end = _extract_parenthesized(s, i)
        # 将内部内容作为值存储
        node_type = 'constant' if key.startswith("IntCon") or key.startswith("IntConst") else 'terminal'
        value = whole[len("(" + key): -1].strip()
        return ExpressionNode(node_type=node_type, value=value, children=[], position=i), end
    if key == "Operator":
        # 格式：(Operator OP_NAME Next: <子表达式> [, <子表达式>...])
        j = _skip_ws(s, j)
        op_name, j = _read_token(s, j)
        # 找到 "Next:" 标记
        rest = s[j:]
        next_idx = rest.find("Next:")
        if next_idx < 0:
            raise ParseError(f"Operator 缺失 Next: @ {j}")
        cursor = j + next_idx + len("Next:")
        children = []
        cursor = _skip_ws(s, cursor)
        # 持续读取子表达式
        while cursor < len(s):
            cursor = _skip_ws(s, cursor)
            if s[cursor] != '(': 
                # 兜底：裸值直接识别为 constant/terminal
                val_start = cursor
                while cursor < len(s) and s[cursor] not in ',)':
                    cursor += 1
                val = s[val_start:cursor].strip()
                if val:
                    if val.isdigit() or val.startswith("'") or val.replace('.', '', 1).isdigit() or ("'" in val and 'b' in val) or '[' in val:
                        children.append(ExpressionNode("constant", val, [], position=val_start))
                    else:
                        children.append(ExpressionNode("terminal", val, [], position=val_start))
                if cursor < len(s) and s[cursor] == ',':
                    cursor += 1
                    continue
                if cursor < len(s) and s[cursor] == ')':
                    return ExpressionNode("operator", op_name, children, position=i), cursor+1
                continue
            child, cursor = parse_expression(s, cursor)
            children.append(child)
            cursor = _skip_ws(s, cursor)
            if cursor < len(s) and s[cursor] == ',':
                cursor += 1
                continue
            if cursor < len(s) and s[cursor] == ')':
                return ExpressionNode("operator", op_name, children, position=i), cursor+1
        raise ParseError("Operator 未正常闭合")
    if key == "Concat":
        # 格式：(Concat Next: <expr>, <expr>, ...)
        whole, end = _extract_parenthesized(s, i)
        next_pos = whole.find("Next:")
        if next_pos < 0:
            raise ParseError("Concat 缺失 Next:")
        payload = whole[next_pos+5:-1]
        parts = _split_top_exprs(payload)
        children = []
        for part in parts:
            node, _ = parse_expression(part.strip(), 0)
            children.append(node)
        return ExpressionNode("concat", "Concat", children, position=i), end
    if key == "Branch":
        # 格式：(Branch Cond:(<expr>) True:(<expr>) [False:(<expr>)])
        whole, end = _extract_parenthesized(s, i)
        cond_expr = _extract_tagged_subexpr(whole, "Cond:")
        true_expr = _extract_tagged_subexpr(whole, "True:")
        false_expr = _extract_tagged_subexpr(whole, "False:", required=False)
        children = []
        if cond_expr is None:
            raise ParseError("Branch missing Cond expression")
        if true_expr is None:
            raise ParseError("Branch missing True expression")
        cond_node, _ = parse_expression(cond_expr, 0)
        true_node, _ = parse_expression(true_expr, 0)
        children.extend([cond_node, true_node])
        if false_expr:
            false_node, _ = parse_expression(false_expr, 0)
            children.append(false_node)
        return ExpressionNode("branch", "Branch", children, position=i), end
    if key == "Partselect":
        # 格式：(Partselect Var:(<expr>) MSB:(<expr>) LSB:(<expr>))
        whole, end = _extract_parenthesized(s, i)
        var_expr = _extract_tagged_subexpr(whole, "Var:")
        msb_expr = _extract_tagged_subexpr(whole, "MSB:")
        lsb_expr = _extract_tagged_subexpr(whole, "LSB:")
        children = []
        if var_expr is None or msb_expr is None or lsb_expr is None:
            raise ParseError("Partselect 缺少必需的子表达式")
        var_node, _ = parse_expression(var_expr, 0)
        msb_node, _ = parse_expression(msb_expr, 0)
        lsb_node, _ = parse_expression(lsb_expr, 0)
        children.extend([var_node, msb_node, lsb_node])
        return ExpressionNode("partselect", "Partselect", children, position=i), end
    # 对于未知关键字，整体按unknown处理
    whole, end = _extract_parenthesized(s, i)
    return ExpressionNode("unknown", whole, [], position=i), end

def _split_top_exprs(s: str) -> List[str]:
    """根据逗号分隔顶层子表达式，利用括号深度判断切分"""
    parts = []
    depth = 0
    start = 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(s[start:i])
            start = i + 1
    tail = s[start:].strip()
    if tail:
        parts.append(tail)
    return parts

def _extract_tagged_subexpr(whole: str, tag: str, required: bool = True) -> Optional[str]:
    """
    从整体字符串中提取标记后的括号内子表达式
    例如从 "Cond:(<expr>)" 提取括号内内容
    """
    idx = whole.find(tag)
    if idx < 0:
        if required:
            raise ParseError(f"缺失标记 {tag}")
        return None
    i = idx + len(tag)
    i = _skip_ws(whole, i)
    if i >= len(whole):
        if required:
            raise ParseError(f"{tag} 后缺表达式")
        return None
    if whole[i] != '(': 
        # 兜底：直接提取到下一个空白/逗号/右括号
        j = i
        while j < len(whole) and whole[j] not in ',) \n\t':
            j += 1
        return whole[i:j]
    sub, _ = _extract_parenthesized(whole, i)
    return sub

def evaluate_linearity(node: ExpressionNode, linear_ops: Set[str]) -> Dict:
    """
    递归评估 AST 中节点的线性性：
    - Terminal/constant 为线性
    - Operator 节点：如果本身在线性集合中且所有子节点线性，则整体线性，否则非线性
    - Concat 节点：所有子节点均线性为线性，否则非线性
    - Branch 默认非线性（可扩展）
    - Partselect 仅检查 Var 子节点
    """
    if node.node_type in ("terminal", "constant"):
        return {"is_linear": True, "reasons": []}
    if node.node_type == "operator":
        child_infos = [evaluate_linearity(child, linear_ops) for child in node.children]
        if all(info["is_linear"] for info in child_infos) and node.value in linear_ops:
            return {"is_linear": True, "reasons": []}
        reasons = []
        if node.value not in linear_ops:
            reasons.append(f"非线性算子:{node.value}")
        for info in child_infos:
            if not info["is_linear"]:
                reasons.extend(info["reasons"])
        return {"is_linear": False, "reasons": reasons}
    if node.node_type == "concat":
        child_infos = [evaluate_linearity(child, linear_ops) for child in node.children]
        if all(info["is_linear"] for info in child_infos):
            return {"is_linear": True, "reasons": []}
        reasons = []
        for info in child_infos:
            if not info["is_linear"]:
                reasons.extend(info["reasons"])
        return {"is_linear": False, "reasons": reasons}
    if node.node_type == "partselect":
        # 只评价 Var 子节点（第一个子节点），MSB和LSB通常为常量
        var_info = evaluate_linearity(node.children[0], linear_ops)
        return var_info
    if node.node_type == "branch":
        # 条件分支默认认为非线性
        return {"is_linear": False, "reasons": ["条件分支表达式"]}
    # 未识别类型视为非线性
    return {"is_linear": False, "reasons": ["未知节点类型"]}

import importlib.util

class CorrectedLinearityAnalyzer:
    def __init__(self, linearity_mode: str = 'arith', verilog_file: str = "", module_prefix: str = ""):
        """
        linearity_mode: 'arith' | 'gf2'
        verilog_file: 可选，Verilog 文件路径，用于信号-行号映射
        module_prefix: 可选，信号名前缀（如 'alu.'）
        """
        self.linearity_mode = linearity_mode
        # 保存初始化参数，便于后续导出时写回
        self.verilog_file = verilog_file
        self.module_prefix = module_prefix
        self.linear_operators = {
            'Plus', 'Minus', 'UnaryMinus',
            'Concat', 'Partselect'
        }
        if self.linearity_mode == 'gf2':
            self.linear_operators = set(self.linear_operators)
            self.linear_operators.add('Xor')
        self.nonlinear_operators = {
            'And', 'Or', 'Xor', 'Xnor',
            'Unot', 'Unor', 'Uand', 'Uxor',
            'Times', 'Divide', 'Mod',
            'Eq', 'NotEq', 'Lt', 'Gt', 'Lte', 'Gte',
            'Sll', 'Srl'
        }
        self.signal_analyses: Dict[str, Dict] = {}
        self.total_expressions = 0
        self.signal_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.bind_payloads: List[Dict] = []
        # --- 行号映射 ---
        self.verilog_signal_linenos = None
        if verilog_file:
            # 动态导入 verilog_parser
            verilog_parser = None
            try:
                import esimulator.utils.verilog_parser as verilog_parser
            except ImportError:
                parser_spec = importlib.util.find_spec("esimulator.utils.verilog_parser")
                if parser_spec is not None and getattr(parser_spec, "origin", None):
                    spec = importlib.util.spec_from_file_location("verilog_parser", parser_spec.origin)
                    if spec is not None and spec.loader is not None:
                        verilog_parser = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(verilog_parser)
            if verilog_parser:
                try:
                    self.verilog_signal_linenos = verilog_parser.parse_verilog_for_line_numbers(verilog_file, module_prefix)
                except Exception as e:
                    print(f"[LinearityAnalyzer] Verilog 行号解析失败: {e}")
                    self.verilog_signal_linenos = None
            else:
                print("[LinearityAnalyzer] 未找到 verilog_parser，无法解析行号。")
                self.verilog_signal_linenos = None
    
    def analyze_dfg_file(self, file_path: str, *, export_graph_json: Optional[str] = None,
                         export_graph_gexf: Optional[str] = None) -> Dict:
        """分析DFG文件，按表达式级别进行线性分析并可导出图结构

        参数:
            file_path: DFG 源文件路径
            export_graph_json: 若提供, 导出包含节点属性与边的 JSON 文件
            export_graph_gexf: 若提供且安装 networkx, 以 gexf 形式导出图
        返回:
            综合报告 dict (新增 'graph' 键, 内含 nodes 与 edges )
        """
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 兼容 CRLF 与行尾空白; 确保能正确分割多个 Bind 片段
        bind_pattern = r'\(Bind\s+dest:([^\s]+).*?tree:(.*?)\)\s*(?=\r?\n\(Bind|\r?\nBranch:|\r?\n\r?\n|\Z)'
        matches = list(re.finditer(bind_pattern, content, re.DOTALL))
        self.total_expressions = len(matches)
        print(f"找到 {self.total_expressions} 个信号表达式")

        for match in matches:
            signal_name = match.group(1)
            tree_expr = match.group(2).strip()
            try:
                # 统一路径：所有绑定都解析为 AST（包括 Terminal/Const）
                ast_root, _ = parse_expression(tree_expr, 0)
                # 注入 is_linear 到节点
                self._annotate_linearity(ast_root)
                lin_info = evaluate_linearity(ast_root, self.linear_operators)

                ops: List[str] = []
                terminals: Set[str] = set()

                def collect_ops(node: ExpressionNode):
                    if node.node_type == 'operator':
                        ops.append(node.value)
                    elif node.node_type == 'terminal':
                        term_name = node.value.strip().split()[0]
                        if not term_name.isdigit():
                            terminals.add(term_name)
                    for child in node.children:
                        collect_ops(child)

                collect_ops(ast_root)
                # 对于 Terminal/Const，复杂度标记为 simple；其余为 complex
                complexity = 'simple' if ast_root.node_type in ('terminal', 'constant') else 'complex'
                reason = '线性AST' if lin_info['is_linear'] else ','.join(sorted(set(lin_info['reasons'])))
                analysis = {
                    'is_linear': lin_info['is_linear'],
                    'reason': reason,
                    'complexity': complexity,
                    'operators': ops,
                    'expression_type': ast_root.node_type
                }

                # 填充依赖（alias 以前不会进入这里，现统一处理）
                for src in terminals:
                    if src != signal_name:
                        self.signal_dependencies[signal_name].add(src)

                # 构建 Bind 粒度导出：AST + operator/workset mask + 可融合邻接
                bind_payload = self._build_bind_payload(signal_name, ast_root)
                self.bind_payloads.append(bind_payload)
                self.signal_analyses[signal_name] = analysis
            except Exception as e:
                print(f"分析信号 {signal_name} 时出错: {e}")
                self.signal_analyses[signal_name] = {
                    'is_linear': False,
                    'reason': f'解析错误: {str(e)}',
                    'complexity': 'error',
                    'operators': [],
                    'expression_type': 'unknown'
                }

        report = self._generate_comprehensive_report()
        graph_payload = self._build_graph_payload()
        report['graph'] = graph_payload
        if export_graph_json:
            self._export_graph_json(graph_payload, export_graph_json)
        if export_graph_gexf and nx is not None:
            self._export_graph_gexf(graph_payload, export_graph_gexf)
        return report

    # ---------------- Public: 导出 Bind 级 JSON ----------------
    def export_bind_masks(self, dfg_path: str, out_path: str, *, omit_trivial: bool = False, include_human_labels: bool = True) -> str:
        """对 DFG 进行解析并导出每个 Bind 的 AST+mask+可融合邻接。

        返回: 写入的文件路径
        """
        # 清空历史绑定载荷
        self.bind_payloads = []
        # 运行一次分析（内部会填充 bind_payloads）
        self.analyze_dfg_file(dfg_path)
        # 在导出前补充 Verilog 覆盖（对于无 bind 的参与信号也生成合成条目）
        self._ensure_verilog_signal_coverage()
        binds = self.bind_payloads
        # 可选：过滤掉没有任何可掩码单元的 trivial 绑定
        if omit_trivial:
            binds = [b for b in binds if not b.get('is_trivial', False)]
        # 可选：附加人类可读标签（为了兼容性，同时保留原有字段）
        if include_human_labels:
            for b in binds:
                if 'workset_labels' not in b:
                    # 兼容旧字段名
                    b['workset_labels'] = self._build_workset_labels(b)
        payload = {
            'file': dfg_path,
            # 若存在行号映射，则输出实际 verilog 文件路径，否则为 None
            'verilog_file': (self.verilog_file if self.verilog_signal_linenos else None),
            'binds': binds,
            'total_binds': len(binds)
        }
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Bind 掩码(JSON)已导出: {out_path}")
        return str(p)

    # ---------------- 图构建与导出 ----------------
    def _build_graph_payload(self) -> Dict:
        """构建图数据结构 {nodes: {name: attrs}, edges: [[src,dst], ...]}"""
        nodes = {}
        for sig, analysis in self.signal_analyses.items():
            nodes[sig] = {
                'is_linear': bool(analysis['is_linear']),
                'reason': analysis['reason'],
                'operators': analysis['operators'],
                'expression_type': analysis['expression_type'],
                # 反向记录其依赖(源)数量
                'in_degree_sources': len(self.signal_dependencies.get(sig, []))
            }
        edges = []
        for dest, sources in self.signal_dependencies.items():
            for src in sources:
                # 仅在源信号存在分析信息时建立边 (忽略外部输入端口不在 Bind 列表情况)
                edges.append([src, dest])
        return {'nodes': nodes, 'edges': edges}

    def _export_graph_json(self, graph_payload: Dict, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(graph_payload, f, ensure_ascii=False, indent=2)
        print(f"图数据(JSON)已导出: {path}")

    def _export_graph_gexf(self, graph_payload: Dict, path: str):
        if nx is None:
            print("未安装 networkx, 跳过 gexf 导出")
            return
        G = nx.DiGraph()
        for name, attrs in graph_payload['nodes'].items():
            G.add_node(name, **attrs)
        for src, dst in graph_payload['edges']:
            G.add_edge(src, dst)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        nx.write_gexf(G, path)
        print(f"图数据(GEXF)已导出: {path}")
    
    # ---------------- AST/掩码/可融合构建 ----------------
    def _annotate_linearity(self, node: ExpressionNode) -> bool:
        """自底向上计算并写回 node.is_linear，返回该节点线性性。"""
        if node.node_type in ("terminal", "constant"):
            node.is_linear = True
            return True
        if node.node_type == "operator":
            child_lin = all(self._annotate_linearity(ch) for ch in node.children)
            node.is_linear = (child_lin and node.value in self.linear_operators)
            return bool(node.is_linear)
        if node.node_type == "concat":
            node.is_linear = all(self._annotate_linearity(ch) for ch in node.children)
            return bool(node.is_linear)
        if node.node_type == "partselect":
            # 仅 Var 子节点决定线性性
            if node.children:
                var_lin = self._annotate_linearity(node.children[0])
            else:
                var_lin = False
            # 仍然标记整体线性性，便于上层统计
            for ch in node.children[1:]:
                self._annotate_linearity(ch)
            node.is_linear = var_lin
            return bool(node.is_linear)
        if node.node_type == "branch":
            # 递归子树以确保子节点 is_linear 完整
            for ch in node.children:
                self._annotate_linearity(ch)
            node.is_linear = False
            return False
        # unknown
        for ch in node.children:
            self._annotate_linearity(ch)
        node.is_linear = False
        return False

    def _serialize_ast(self, root: ExpressionNode) -> Tuple[Dict[str, Dict], int, Dict[int, ExpressionNode]]:
        """扁平化 AST 为 {id: attrs}，返回 (nodes_dict, root_id, id->node 映射)。"""
        nodes: Dict[str, Dict] = {}
        id_map: Dict[int, ExpressionNode] = {}
        next_id = 0

        def alloc_id() -> int:
            nonlocal next_id
            nid = next_id
            next_id += 1
            return nid

        def walk(n: ExpressionNode) -> int:
            nid = alloc_id()
            id_map[nid] = n
            child_ids = [walk(c) for c in n.children]
            nodes[str(nid)] = {
                'id': nid,
                'type': n.node_type,
                'value': n.value,
                'children': child_ids,
                'is_linear': bool(n.is_linear),
            }
            # mark：
            # - operator: 1/0
            # - concat/partselect: 1/0（用于 workset 掩码）
            # - 其他: None
            if n.node_type == 'operator':
                nodes[str(nid)]['mark'] = 1 if n.is_linear else 0
                nodes[str(nid)]['intrinsic_linear'] = 1 if self._op_intrinsic_linear(n.value) else 0
            elif n.node_type in ('concat', 'partselect'):
                nodes[str(nid)]['mark'] = 1 if n.is_linear else 0
                nodes[str(nid)]['intrinsic_linear'] = 1
            elif n.node_type in ('terminal', 'constant'):
                nodes[str(nid)]['mark'] = None
                nodes[str(nid)]['intrinsic_linear'] = 1
            elif n.node_type == 'branch':
                nodes[str(nid)]['mark'] = None
                nodes[str(nid)]['intrinsic_linear'] = 0
            else:
                nodes[str(nid)]['mark'] = None
                nodes[str(nid)]['intrinsic_linear'] = 0
            return nid

        root_id = walk(root)
        return nodes, root_id, id_map

    def _collect_operator_order_and_mask(self, nodes_dict: Dict[str, Dict], root_id: int) -> Tuple[List[int], List[int]]:
        order: List[int] = []
        mask: List[int] = []

        def dfs(nid: int):
            n = nodes_dict[str(nid)]
            if n['type'] == 'operator':
                order.append(nid)
                mask.append(int(n.get('mark', 0) or 0))
            for cid in n['children']:
                dfs(cid)

        dfs(root_id)
        return order, mask

    def _collect_workset_order_and_mask(self, nodes_dict: Dict[str, Dict], root_id: int) -> Tuple[List[int], List[int]]:
        """收集可掩码工作集（operator + concat + partselect）的顺序与掩码。"""
        order: List[int] = []
        mask: List[int] = []

        def dfs(nid: int):
            n = nodes_dict[str(nid)]
            if n['type'] in ('operator', 'concat', 'partselect'):
                order.append(nid)
                m = n.get('mark', None)
                mask.append(int(m) if isinstance(m, int) else 0)
            for cid in n['children']:
                dfs(cid)

        dfs(root_id)
        return order, mask

    def _has_branch(self, nodes_dict: Dict[str, Dict]) -> bool:
        for k, v in nodes_dict.items():
            if v.get('type') == 'branch':
                return True
        return False

    def _build_fusable_adjacency(self, nodes_dict: Dict[str, Dict], root_id: int) -> List[List[int]]:
        """可融合关系：线性工作集（operator/concat/partselect）父子之间建立无向边。"""
        edges: Set[Tuple[int, int]] = set()

        def dfs(nid: int):
            n = nodes_dict[str(nid)]
            for cid in n['children']:
                c = nodes_dict[str(cid)]
                # 不穿越分支；仅在父子均为线性 operator 时建立边
                if n['type'] == 'branch' or c['type'] == 'branch':
                    pass
                else:
                    if n['type'] in ('operator', 'concat', 'partselect') and c['type'] in ('operator', 'concat', 'partselect'):
                        if n.get('mark') == 1 and c.get('mark') == 1:
                            a, b = sorted((nid, cid))
                            edges.add((a, b))
                dfs(cid)

        dfs(root_id)
        return [[a, b] for (a, b) in sorted(edges)]

    def _build_bind_payload(self, dest: str, ast_root: ExpressionNode) -> Dict:
        nodes_dict, root_id, id_map = self._serialize_ast(ast_root)
        operator_order, operator_mask = self._collect_operator_order_and_mask(nodes_dict, root_id)
        workset_order, workset_mask = self._collect_workset_order_and_mask(nodes_dict, root_id)
        fusable_adj = self._build_fusable_adjacency(nodes_dict, root_id)
        bind_has_branch = self._has_branch(nodes_dict)
        sources = sorted(self.signal_dependencies.get(dest, []))
        if not sources and ast_root.node_type == 'terminal':
            sources = [self._extract_terminal_name(ast_root.value)]
        const_value: Optional[str] = None
        if ast_root.node_type == 'constant':
            const_value = self._extract_const_repr(ast_root.value)
            if not sources:
                sources = [f"CONST({const_value})"]

        bind_kind = (
            'alias' if ast_root.node_type == 'terminal' else
            'constant' if ast_root.node_type == 'constant' else
            'branch' if bind_has_branch else
            'opchain'
        )
        maskable_count = len(workset_order)
        is_trivial = (maskable_count == 0)

        workset_intrinsic_mask: List[int] = []
        for nid in workset_order:
            n = nodes_dict[str(nid)]
            workset_intrinsic_mask.append(int(n.get('intrinsic_linear', 0)))

        # 绑定内的运算符类型集合（便于消费方直接读取）
        operator_types: List[str] = []
        for k, n in nodes_dict.items():
            if n.get('type') == 'operator':
                val = n.get('value')
                if isinstance(val, str):
                    operator_types.append(val)
        operator_types = sorted(list(set(operator_types)))

        # --- 行号映射 ---
        dest_location = None
        source_locations = []
        if self.verilog_signal_linenos:
            dest_location = self.verilog_signal_linenos.get(dest, None)
            for s in sources:
                # 只对普通信号查找行号，常量/特殊名不查
                if s.startswith("CONST("):
                    source_locations.append(None)
                else:
                    source_locations.append(self.verilog_signal_linenos.get(s, None))
        else:
            dest_location = None
            source_locations = [None for _ in sources]

        payload = {
            'dest': dest,
            'dest_location': dest_location,
            'ast': {
                'nodes': nodes_dict,
                'root': root_id
            },
            'operator_order': operator_order,
            'operator_mask': operator_mask,
            'operator_types': operator_types,
            'workset_order': workset_order,
            'workset_mask': workset_mask,
            'workset_intrinsic_mask': workset_intrinsic_mask,
            'fusable_adj': fusable_adj,
            'bind_has_branch': bind_has_branch,
            'sources': sources,
            'source_locations': source_locations,
            'operator_count': len(operator_order),
            'bind_kind': bind_kind,
            'maskable_count': maskable_count,
            'is_trivial': is_trivial
        }
        if const_value is not None:
            payload['const_value'] = const_value
        payload['workset_labels'] = self._build_workset_labels(payload)
        return payload

    def _ensure_verilog_signal_coverage(self):
        """补充：对于出现在 Verilog 且参与 DFG（作为 dest 或 source）但没有对应 bind 的信号，
        生成合成条目，至少包含行号与其被使用到的运算符类型集合。
        前置条件：self.verilog_signal_linenos 可用。
        """
        if not self.verilog_signal_linenos:
            return
        # 已有的 bind 目的集合
        existing_dests = {b.get('dest') for b in self.bind_payloads}
        # 作为 source 参与的信号集合
        involved_sources = set()
        for b in self.bind_payloads:
            for s in b.get('sources', []):
                involved_sources.add(s)
        # 目标集合：verilog 出现 且 (是 bind 目标 或 作为 source 参与)
        candidates = set(self.verilog_signal_linenos.keys()) & (existing_dests | involved_sources)
        to_create = [sig for sig in candidates if sig not in existing_dests]
        if not to_create:
            return
        # 反向索引：signal -> 在哪些 bind 中作为 source 出现
        usage_map: Dict[str, List[Dict]] = defaultdict(list)
        for b in self.bind_payloads:
            for s in b.get('sources', []):
                usage_map[s].append(b)
        # 为每个缺失的信号创建合成 payload
        for sig in sorted(to_create):
            dest_location = self.verilog_signal_linenos.get(sig)
            # 汇总其参与到的运算符类型集合（来自使用它的 bind 的 operator_types）
            usage_ops: Set[str] = set()
            for b in usage_map.get(sig, []):
                for op in b.get('operator_types', []):
                    usage_ops.add(op)
            # 构造一个最小 AST（单个 terminal）
            nodes_dict = {
                "0": {
                    'id': 0,
                    'type': 'terminal',
                    'value': sig,
                    'children': [],
                    'is_linear': True,
                    'mark': None,
                    'intrinsic_linear': 1,
                }
            }
            payload = {
                'dest': sig,
                'dest_location': dest_location,
                'ast': {
                    'nodes': nodes_dict,
                    'root': 0
                },
                'operator_order': [],
                'operator_mask': [],
                'operator_types': [],
                'workset_order': [],
                'workset_mask': [],
                'workset_intrinsic_mask': [],
                'fusable_adj': [],
                'bind_has_branch': False,
                'sources': [],
                'source_locations': [],
                'operator_count': 0,
                'bind_kind': 'verilog_only',
                'maskable_count': 0,
                'is_trivial': True,
                'workset_labels': [],
                # 参与到其它绑定中的运算符类型（基于使用）
                'usage_operator_types': sorted(usage_ops),
                'usage_bind_count': len(usage_map.get(sig, [])),
            }
            self.bind_payloads.append(payload)

    def _op_intrinsic_linear(self, op_name: str) -> bool:
        """返回算子本征线性标签（不考虑子节点）。"""
        if op_name in self.linear_operators:
            return True
        # gf2 模式下，Xor 已加入 linear_operators；这里兜底即可
        return False

    def _extract_terminal_name(self, terminal_value: str) -> str:
        """从 Terminal 节点的 value 文本中提取信号名（最左 token）。"""
        return terminal_value.strip().split()[0]

    def _extract_const_repr(self, const_value: str) -> str:
        """提取常量的简洁表示。直接返回去首尾空白的原文更稳妥。"""
        return const_value.strip()

    def _build_workset_labels(self, bind_payload: Dict) -> List[str]:
        """构建人类可读的工作集标签，例如 "dest#op0:Or" / "dest#ps2:Partselect"。"""
        dest = bind_payload.get('dest', '')
        ast_nodes: Dict[str, Dict] = bind_payload.get('ast', {}).get('nodes', {})
        labels: List[str] = []
        for idx, nid in enumerate(bind_payload.get('workset_order', [])):
            n = ast_nodes.get(str(nid), {})
            t = n.get('type')
            if t == 'operator':
                label_kind = n.get('value', 'Op')
            elif t in ('concat', 'partselect'):
                label_kind = t.capitalize()
            else:
                label_kind = t or 'Node'
            labels.append(f"{dest}#op{idx}:{label_kind}")
        return labels
    
    
    
    def _generate_comprehensive_report(self) -> Dict:
        """生成全面的分析报告"""
        linear_count = sum(1 for analysis in self.signal_analyses.values() if analysis['is_linear'])
        nonlinear_count = self.total_expressions - linear_count
        
        complexity_stats = defaultdict(int)
        expression_type_stats = defaultdict(int)
        nonlinear_reasons = defaultdict(int)
        
        for signal, analysis in self.signal_analyses.items():
            complexity_stats[analysis['complexity']] += 1
            expression_type_stats[analysis['expression_type']] += 1
            if not analysis['is_linear']:
                reason = analysis['reason'].split(':')[0] if ':' in analysis['reason'] else analysis['reason']
                nonlinear_reasons[reason] += 1
        
        operator_usage = defaultdict(int)
        for analysis in self.signal_analyses.values():
            for op in analysis['operators']:
                operator_usage[op] += 1
        
        return {
            'summary': {
                'total_expressions': self.total_expressions,
                'linear_expressions': linear_count,
                'nonlinear_expressions': nonlinear_count,
                'linearity_ratio': linear_count / self.total_expressions if self.total_expressions > 0 else 0
            },
            'complexity_distribution': dict(complexity_stats),
            'expression_type_distribution': dict(expression_type_stats),
            'nonlinear_reasons': dict(nonlinear_reasons),
            'operator_usage': dict(operator_usage),
            'detailed_analyses': self.signal_analyses
        }

def analyze_real_dfg(file_name):
    """分析真实的DFG文件"""
    analyzer = CorrectedLinearityAnalyzer()
    dfg_file = f"/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/{file_name}"
    
    # 同时导出图 JSON 到 results 目录
    graph_json_path = f"results/{file_name[:-4]}_linearity_graph.json"
    report = analyzer.analyze_dfg_file(dfg_file, export_graph_json=graph_json_path)
    # 导出 Bind 掩码 JSON
    bind_json_path = f"results/{file_name[:-4]}_bind_masks.json"
    analyzer.export_bind_masks(dfg_file, bind_json_path)
    print(f"\n=== 分析结果 ===")
    summary = report['summary']
    print(f"总表达式数: {summary['total_expressions']}")
    print(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})")
    print(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})")
    
    print(f"\n表达式类型分布:")
    for expr_type, count in report['expression_type_distribution'].items():
        percentage = count / summary['total_expressions'] * 100
        print(f"  {expr_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n运算符使用统计（前10位）:")
    sorted_ops = sorted(report['operator_usage'].items(), key=lambda x: x[1], reverse=True)
    for op, count in sorted_ops[:10]:
        op_type = "线性" if op in analyzer.linear_operators else "非线性"
        print(f"  {op} ({op_type}): {count}")
    
    print(f"\n生成修正报告...")
    with open(f"results/{file_name[:-4]}_linearity_analysis.txt", "w", encoding="utf-8") as f:
        f.write(f"{file_name}线性分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write("分析结果:\n")
        f.write("-" * 15 + "\n")
        f.write(f"总表达式数: {summary['total_expressions']}\n")
        f.write(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})\n")
        f.write(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})\n\n")
        f.write("表达式类型分布:\n")
        f.write("-" * 20 + "\n")
        for expr_type, count in report['expression_type_distribution'].items():
            percentage = count / summary['total_expressions'] * 100
            f.write(f"{expr_type:<15}: {count:>3} ({percentage:>5.1f}%)\n")
        f.write(f"\n非线性原因分析:\n")
        f.write("-" * 20 + "\n")
        for reason, count in report['nonlinear_reasons'].items():
            f.write(f"{reason}: {count}\n")
        f.write(f"\n详细信号分析:\n")
        f.write("-" * 20 + "\n")
        for signal, analysis in sorted(report['detailed_analyses'].items()):
            linearity = "线性" if analysis['is_linear'] else "非线性"
            f.write(f"{signal:<20}: {linearity:<6} - {analysis['reason']}\n")
    
    print(f"报告已保存到: results/{file_name[:-4]}_linearity_analysis.txt")
    print(f"图 JSON 已保存到: {graph_json_path}")

if __name__ == "__main__":
    analyze_real_dfg('4004_dfg.txt')
