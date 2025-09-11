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
    if i >= len(s) or s[i] != '(':
        raise ParseError(f"期望 '(' 于位置 {i}")
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
                if s[cursor] == ',':
                    cursor += 1
                    continue
                if s[cursor] == ')':
                    return ExpressionNode("operator", op_name, children, position=i), cursor+1
                raise ParseError(f"Operator 中遇到未知字符 '{s[cursor]}' 于 {cursor}")
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
    if i >= len(whole) or whole[i] != '(':
        raise ParseError(f"{tag} 后缺 '('")
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

class CorrectedLinearityAnalyzer:
    
    def __init__(self):
        # 线性运算符定义（仅支持基本算术及位拼接操作）
        self.linear_operators = {
            'Plus', 'Minus', 'UnaryMinus',  # 基本算术运算
            'Concat', 'Partselect'          # 位操作（线性组合）
        }
        
        # 非线性运算符定义
        self.nonlinear_operators = {
            'And', 'Or', 'Xor', 'Xnor',     # 逻辑运算
            'Unot', 'Unor', 'Uand', 'Uxor',  # 归约运算
            'Times', 'Divide', 'Mod',       # 乘除运算
            'Eq', 'NotEq', 'Lt', 'Gt', 'Lte', 'Gte',  # 比较运算
            'Sll', 'Srl'                    # 位移运算
        }
        
        self.signal_analyses: Dict[str, Dict] = {}
        self.total_expressions = 0
        # 依赖映射: dest -> set(sources)
        self.signal_dependencies: Dict[str, Set[str]] = defaultdict(set)
    
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
                if tree_expr.startswith('(Terminal '):
                    analysis = {
                        'is_linear': True,
                        'reason': '直接终端赋值',
                        'complexity': 'simple',
                        'operators': [],
                        'expression_type': 'terminal'
                    }
                elif tree_expr.startswith('(IntCon') or tree_expr.startswith('(IntConst'):
                    analysis = {
                        'is_linear': True,
                        'reason': '常量赋值',
                        'complexity': 'simple',
                        'operators': [],
                        'expression_type': 'constant'
                    }
                else:
                    try:
                        ast_root, _ = parse_expression(tree_expr, 0)
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
                        reason = '线性AST' if lin_info['is_linear'] else ','.join(sorted(set(lin_info['reasons'])))
                        analysis = {
                            'is_linear': lin_info['is_linear'],
                            'reason': reason,
                            'complexity': 'complex',
                            'operators': ops,
                            'expression_type': ast_root.node_type
                        }
                        for src in terminals:
                            if src != signal_name:
                                self.signal_dependencies[signal_name].add(src)
                    except Exception as e_ast:
                        print(f"AST解析失败,回退旧逻辑: {e_ast}")
                        if tree_expr.startswith('(Branch '):
                            analysis = self._analyze_branch_expression(tree_expr)
                        elif tree_expr.startswith('(Concat '):
                            analysis = self._analyze_concat_expression(tree_expr)
                        elif tree_expr.startswith('(Operator '):
                            analysis = self._analyze_operator_expression(tree_expr)
                        else:
                            analysis = {
                                'is_linear': False,
                                'reason': f'解析错误: {str(e_ast)}',
                                'complexity': 'error',
                                'operators': [],
                                'expression_type': 'unknown'
                            }
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
    
    def _analyze_operator_expression(self, expr: str) -> Dict:
        """旧方式：分析运算符表达式，基于正则扫描"""
        operators_found = []
        is_linear = True
        nonlinear_reason = None
        
        operator_pattern = r'\(Operator (\w+) Next:'
        matches = list(re.finditer(operator_pattern, expr))
        
        for match in matches:
            operator = match.group(1)
            operators_found.append(operator)
            if operator in self.nonlinear_operators:
                is_linear = False
                if nonlinear_reason is None:
                    nonlinear_reason = f'包含非线性运算符: {operator}'
        
        if '(Branch ' in expr:
            is_linear = False
            if nonlinear_reason is None:
                nonlinear_reason = '包含条件分支'
        
        op_count = len(operators_found)
        if op_count <= 1:
            complexity = 'simple'
        elif op_count <= 5:
            complexity = 'moderate'
        else:
            complexity = 'complex'
        
        reason = nonlinear_reason if not is_linear else f'仅包含线性运算符: {operators_found}'
        return {
            'is_linear': is_linear,
            'reason': reason,
            'complexity': complexity,
            'operators': operators_found,
            'expression_type': 'operator'
        }
    
    def _analyze_branch_expression(self, expr: str) -> Dict:
        """旧方式：分析分支表达式（条件分支默认非线性）"""
        operator_pattern = r'\(Operator (\w+) Next:'
        operators = re.findall(operator_pattern, expr)
        return {
            'is_linear': False,
            'reason': '条件分支表达式（本质非线性）',
            'complexity': 'complex',
            'operators': operators,
            'expression_type': 'branch'
        }
    
    def _analyze_concat_expression(self, expr: str) -> Dict:
        """旧方式：分析拼接表达式，检查内部运算符的线性性"""
        operator_pattern = r'\(Operator (\w+) Next:'
        operators = re.findall(operator_pattern, expr)
        is_linear = True
        for op in operators:
            if op in self.nonlinear_operators:
                is_linear = False
                break
        reason = '线性拼接' if is_linear else '拼接中包含非线性子表达式'
        return {
            'is_linear': is_linear,
            'reason': reason,
            'complexity': 'moderate',
            'operators': operators,
            'expression_type': 'concat'
        }
    
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
    
    print(f"\n3. 生成修正报告...")
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
    analyze_real_dfg('demo_dfg.txt')
