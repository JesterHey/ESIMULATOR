#!/usr/bin/env python3
"""
改进的表达式分析器
实现真正的表达式树解析和整体线性分析
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Union
import json

@dataclass
class ExpressionNode:
    """表达式树节点"""
    node_type: str  # 'operator', 'terminal', 'constant', 'branch'
    value: str      # 运算符名称、终端名称等
    children: List['ExpressionNode']
    is_linear: Optional[bool] = None  # 该子表达式是否线性
    
    def __str__(self):
        if self.node_type == 'operator':
            return f"{self.value}({', '.join(str(child) for child in self.children)})"
        else:
            return self.value

@dataclass  
class ExpressionAnalysis:
    """表达式分析结果"""
    signal_name: str
    expression_tree: ExpressionNode
    is_linear: bool
    total_operators: int
    linear_operators: int
    nonlinear_operators: int
    complexity_level: str  # 'simple', 'moderate', 'complex'
    operator_breakdown: Dict[str, int]

class ImprovedLinearityAnalyzer:
    """改进的线性分析器"""
    
    def __init__(self):
        # 线性运算符
        self.linear_operators = {
            'Plus', 'Minus', 'UnaryMinus', 'Sll', 'Srl', 'Concat', 'Partselect'
        }
        
        # 非线性运算符
        self.nonlinear_operators = {
            'And', 'Or', 'Xor', 'Xnor', 'Unot', 'Unor', 'Uand', 'Uxor',
            'Times', 'Divide', 'Mod', 'Power', 'Eq', 'NotEq', 'Lt', 'Gt', 
            'Lte', 'Gte', 'Land', 'Lor'
        }
        
        self.analyses = []
    
    def parse_dfg_file(self, file_path: str) -> List[ExpressionAnalysis]:
        """解析DFG文件并进行改进的分析"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有Bind表达式
        bind_pattern = r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
        
        for match in re.finditer(bind_pattern, content, re.DOTALL):
            signal_name = match.group(1)
            tree_expr = match.group(2).strip()
            
            # 解析表达式树
            try:
                expression_tree = self._parse_expression_tree(tree_expr)
                analysis = self._analyze_expression(signal_name, expression_tree)
                self.analyses.append(analysis)
            except Exception as e:
                print(f"解析表达式 {signal_name} 时出错: {e}")
                continue
        
        return self.analyses
    
    def _parse_expression_tree(self, expr: str) -> ExpressionNode:
        """递归解析表达式树"""
        expr = expr.strip()
        
        # 处理操作符表达式
        if expr.startswith('(Operator '):
            return self._parse_operator(expr)
        
        # 处理终端表达式
        elif expr.startswith('(Terminal '):
            match = re.match(r'\(Terminal ([^)]+)\)', expr)
            if match:
                return ExpressionNode('terminal', match.group(1), [])
        
        # 处理常量表达式
        elif expr.startswith('(IntConst '):
            match = re.match(r'\(IntConst ([^)]+)\)', expr)
            if match:
                return ExpressionNode('constant', match.group(1), [])
        
        # 处理分支表达式
        elif expr.startswith('(Branch '):
            return self._parse_branch(expr)
        
        # 处理Concat表达式
        elif expr.startswith('(Concat '):
            return self._parse_concat(expr)
        
        # 处理Partselect表达式
        elif expr.startswith('(Partselect '):
            return self._parse_partselect(expr)
        
        # 默认处理
        return ExpressionNode('unknown', expr[:50] + '...', [])
    
    def _parse_operator(self, expr: str) -> ExpressionNode:
        """解析操作符表达式"""
        # 提取操作符名称
        match = re.match(r'\(Operator (\w+) Next:', expr)
        if not match:
            raise ValueError(f"无法解析操作符: {expr[:50]}")
        
        operator = match.group(1)
        
        # 找到Next:后的内容
        next_start = expr.find('Next:') + 5
        remaining = expr[next_start:-1]  # 去掉最后的)
        
        # 解析操作数
        operands = self._parse_operands(remaining)
        
        return ExpressionNode('operator', operator, operands)
    
    def _parse_operands(self, expr: str) -> List[ExpressionNode]:
        """解析操作数列表"""
        operands = []
        pos = 0
        paren_count = 0
        start = 0
        
        while pos < len(expr):
            if expr[pos] == '(':
                paren_count += 1
            elif expr[pos] == ')':
                paren_count -= 1
            elif expr[pos] == ',' and paren_count == 0:
                # 找到一个操作数
                operand_expr = expr[start:pos].strip()
                if operand_expr:
                    operands.append(self._parse_expression_tree(operand_expr))
                start = pos + 1
            pos += 1
        
        # 处理最后一个操作数
        final_operand = expr[start:].strip()
        if final_operand:
            operands.append(self._parse_expression_tree(final_operand))
        
        return operands
    
    def _parse_branch(self, expr: str) -> ExpressionNode:
        """解析分支表达式"""
        # Branch表达式比较复杂，这里简化处理
        return ExpressionNode('branch', 'Branch', [])
    
    def _parse_concat(self, expr: str) -> ExpressionNode:
        """解析拼接表达式"""
        # 简化处理Concat
        return ExpressionNode('operator', 'Concat', [])
    
    def _parse_partselect(self, expr: str) -> ExpressionNode:
        """解析位选择表达式"""
        # 简化处理Partselect
        return ExpressionNode('operator', 'Partselect', [])
    
    def _analyze_expression(self, signal_name: str, tree: ExpressionNode) -> ExpressionAnalysis:
        """分析表达式的线性特征"""
        # 递归分析表达式树
        operator_count = defaultdict(int)
        total_ops = self._count_operators(tree, operator_count)
        
        # 判断整体线性
        is_linear = self._is_expression_linear(tree)
        
        # 计算复杂度
        if total_ops <= 1:
            complexity = 'simple'
        elif total_ops <= 5:
            complexity = 'moderate'
        else:
            complexity = 'complex'
        
        # 统计线性/非线性运算符
        linear_ops = sum(count for op, count in operator_count.items() 
                        if op in self.linear_operators)
        nonlinear_ops = sum(count for op, count in operator_count.items() 
                           if op in self.nonlinear_operators)
        
        return ExpressionAnalysis(
            signal_name=signal_name,
            expression_tree=tree,
            is_linear=is_linear,
            total_operators=total_ops,
            linear_operators=linear_ops,
            nonlinear_operators=nonlinear_ops,
            complexity_level=complexity,
            operator_breakdown=dict(operator_count)
        )
    
    def _count_operators(self, node: ExpressionNode, counter: Dict[str, int]) -> int:
        """递归统计运算符数量"""
        total = 0
        
        if node.node_type == 'operator':
            counter[node.value] += 1
            total += 1
        
        for child in node.children:
            total += self._count_operators(child, counter)
        
        return total
    
    def _is_expression_linear(self, node: ExpressionNode) -> bool:
        """递归判断表达式是否线性"""
        if node.is_linear is not None:
            return node.is_linear
        
        # 终端和常量是线性的
        if node.node_type in ['terminal', 'constant']:
            node.is_linear = True
            return True
        
        # 运算符节点
        if node.node_type == 'operator':
            # 如果运算符本身是非线性的，整个表达式非线性
            if node.value in self.nonlinear_operators:
                node.is_linear = False
                return False
            
            # 如果运算符是线性的，检查所有子表达式
            if node.value in self.linear_operators:
                for child in node.children:
                    if not self._is_expression_linear(child):
                        node.is_linear = False
                        return False
                node.is_linear = True
                return True
        
        # 分支表达式通常是非线性的
        if node.node_type == 'branch':
            node.is_linear = False
            return False
        
        # 默认为非线性
        node.is_linear = False
        return False
    
    def generate_comprehensive_report(self) -> Dict:
        """生成全面的分析报告"""
        total_expressions = len(self.analyses)
        linear_expressions = sum(1 for a in self.analyses if a.is_linear)
        nonlinear_expressions = total_expressions - linear_expressions
        
        # 复杂度统计
        complexity_stats = defaultdict(int)
        for analysis in self.analyses:
            complexity_stats[analysis.complexity_level] += 1
        
        # 运算符统计
        all_operators = defaultdict(int)
        for analysis in self.analyses:
            for op, count in analysis.operator_breakdown.items():
                all_operators[op] += count
        
        return {
            'summary': {
                'total_expressions': total_expressions,
                'linear_expressions': linear_expressions,
                'nonlinear_expressions': nonlinear_expressions,
                'linearity_ratio': linear_expressions / total_expressions if total_expressions > 0 else 0
            },
            'complexity_distribution': dict(complexity_stats),
            'operator_statistics': dict(all_operators),
            'detailed_analyses': self.analyses
        }

def main():
    """测试改进的分析器"""
    print("=== 改进的表达式线性分析器 ===")
    
    analyzer = ImprovedLinearityAnalyzer()
    
    # 先测试简单表达式
    test_exprs = [
        "(Operator Plus Next:(Terminal a),(Terminal b))",
        "(Operator And Next:(Terminal a),(Terminal b))",
        "(Operator Plus Next:(Terminal a),(Operator And Next:(Terminal b),(Terminal c)))"
    ]
    
    print("1. 测试简单表达式:")
    for i, expr in enumerate(test_exprs):
        print(f"\n表达式 {i+1}: {expr}")
        try:
            tree = analyzer._parse_expression_tree(expr)
            is_linear = analyzer._is_expression_linear(tree)
            print(f"   解析结果: {tree}")
            print(f"   线性特征: {'线性' if is_linear else '非线性'}")
        except Exception as e:
            print(f"   解析失败: {e}")
    
    print(f"\n2. 分析DFG文件...")
    # 注意：完整的DFG分析可能需要更多的错误处理
    print("   (由于表达式复杂度很高，完整实现需要更多的解析逻辑)")

if __name__ == "__main__":
    main()
