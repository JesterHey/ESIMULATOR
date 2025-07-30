#!/usr/bin/env python3
"""
正确的线性/非线性运算分析器
基于数学定义：线性运算包括加法(+)、减法(-)、数乘等
非线性运算包括逻辑运算(&, |, ~, ^)、乘法(*)、除法(/)等
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional
import json

@dataclass
class Operation:
    """运算操作"""
    name: str
    operation_type: str  # 'linear' or 'nonlinear'
    operator: str
    operands: List[str]
    location: str
    
    def __str__(self):
        return f"{self.name}: {self.operator}({', '.join(self.operands)}) [{self.operation_type}]"

class CorrectLinearityAnalyzer:
    """正确的线性分析器"""
    
    def __init__(self):
        # 线性运算符（数学上的线性运算）
        self.linear_operators = {
            'Plus': '+',           # 加法
            'Minus': '-',          # 减法
            'UnaryMinus': '-',     # 一元负号
            'Sll': '<<',          # 左移（可视为2的幂次乘法，在数字电路中常视为线性）
            'Srl': '>>',          # 右移（可视为2的幂次除法，在数字电路中常视为线性）
            'Concat': 'concat',    # 位拼接（线性组合）
            'Partselect': 'select' # 位选择（线性提取）
        }
        
        # 非线性运算符
        self.nonlinear_operators = {
            'And': '&',           # 逻辑与
            'Or': '|',            # 逻辑或
            'Xor': '^',           # 逻辑异或
            'Xnor': '~^',         # 逻辑异或非
            'Unot': '~',          # 逻辑非
            'Unor': '~|',         # 归约或非
            'Uand': '&',          # 归约与
            'Uxor': '^',          # 归约异或
            'Times': '*',         # 乘法
            'Divide': '/',        # 除法
            'Mod': '%',           # 模运算
            'Power': '**',        # 幂运算
            'Eq': '==',           # 等于比较
            'NotEq': '!=',        # 不等于比较
            'Lt': '<',            # 小于比较
            'Gt': '>',            # 大于比较
            'Lte': '<=',          # 小于等于比较
            'Gte': '>=',          # 大于等于比较
            'Land': '&&',         # 逻辑与
            'Lor': '||'           # 逻辑或
        }
        
        self.operations = []
        self.signals = {}
    
    def parse_dfg_file(self, file_path: str):
        """解析DFG文件并分析线性/非线性运算"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析信号定义
        self._parse_signals(content)
        
        # 解析绑定表达式中的运算
        self._parse_operations(content)
        
        return self.operations
    
    def _parse_signals(self, content: str):
        """解析信号定义"""
        term_pattern = r'\(Term name:([^\s]+) type:\[(.*?)\]'
        for match in re.finditer(term_pattern, content):
            signal_name = match.group(1)
            signal_types = [t.strip().strip("'") for t in match.group(2).split(',')]
            self.signals[signal_name] = signal_types
    
    def _parse_operations(self, content: str):
        """解析运算操作"""
        # 提取所有Bind表达式
        bind_pattern = r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
        
        for match in re.finditer(bind_pattern, content, re.DOTALL):
            dest_signal = match.group(1)
            tree_expr = match.group(2)
            
            # 从表达式树中提取运算
            operations = self._extract_operations_from_tree(tree_expr, dest_signal)
            self.operations.extend(operations)
    
    def _extract_operations_from_tree(self, tree_expr: str, dest_signal: str) -> List[Operation]:
        """从表达式树中提取运算操作"""
        operations = []
        
        # 查找所有操作符
        operator_pattern = r'\(Operator (\w+) Next:'
        for match in re.finditer(operator_pattern, tree_expr):
            operator = match.group(1)
            
            # 判断运算类型
            if operator in self.linear_operators:
                op_type = 'linear'
                op_symbol = self.linear_operators[operator]
            elif operator in self.nonlinear_operators:
                op_type = 'nonlinear'
                op_symbol = self.nonlinear_operators[operator]
            else:
                op_type = 'unknown'
                op_symbol = operator
            
            # 提取操作数（简化处理）
            operands = self._extract_operands_from_context(tree_expr, match.start())
            
            operation = Operation(
                name=f"{dest_signal}_{operator}_{len(operations)}",
                operation_type=op_type,
                operator=op_symbol,
                operands=operands,
                location=dest_signal
            )
            operations.append(operation)
        
        return operations
    
    def _extract_operands_from_context(self, expr: str, op_pos: int) -> List[str]:
        """从上下文中提取操作数"""
        # 简化的操作数提取 - 查找附近的Terminal引用
        context = expr[max(0, op_pos-100):op_pos+200]
        operands = []
        
        terminal_pattern = r'Terminal ([^\s)]+)'
        for match in re.finditer(terminal_pattern, context):
            operand = match.group(1)
            if operand not in operands:
                operands.append(operand)
        
        return operands[:4]  # 限制操作数数量
    
    def analyze_linearity(self) -> Dict:
        """分析线性度"""
        linear_ops = [op for op in self.operations if op.operation_type == 'linear']
        nonlinear_ops = [op for op in self.operations if op.operation_type == 'nonlinear']
        unknown_ops = [op for op in self.operations if op.operation_type == 'unknown']
        
        total_ops = len(self.operations)
        
        # 统计各种运算符
        op_stats = defaultdict(int)
        for op in self.operations:
            op_stats[f"{op.operator} ({op.operation_type})"] += 1
        
        # 按信号分组统计
        signal_stats = defaultdict(lambda: {'linear': 0, 'nonlinear': 0, 'unknown': 0})
        for op in self.operations:
            signal_stats[op.location][op.operation_type] += 1
        
        analysis = {
            'summary': {
                'total_operations': total_ops,
                'linear_operations': len(linear_ops),
                'nonlinear_operations': len(nonlinear_ops),
                'unknown_operations': len(unknown_ops),
                'linearity_ratio': len(linear_ops) / total_ops if total_ops > 0 else 0,
                'nonlinearity_ratio': len(nonlinear_ops) / total_ops if total_ops > 0 else 0
            },
            'operations': {
                'linear': linear_ops,
                'nonlinear': nonlinear_ops,
                'unknown': unknown_ops
            },
            'operator_statistics': dict(op_stats),
            'signal_statistics': dict(signal_stats)
        }
        
        return analysis

def main():
    """主函数"""
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt"
    
    print("=== 正确的线性/非线性运算分析器 ===")
    print("线性运算: +, -, 位移, 位拼接, 位选择等")
    print("非线性运算: &, |, ^, ~, *, /, 比较运算等")
    print()
    
    # 创建分析器
    analyzer = CorrectLinearityAnalyzer()
    
    print("1. 解析DFG文件...")
    operations = analyzer.parse_dfg_file(dfg_file)
    print(f"   发现 {len(operations)} 个运算操作")
    
    print("\n2. 分析线性度...")
    analysis = analyzer.analyze_linearity()
    
    # 输出分析结果
    summary = analysis['summary']
    print(f"\n=== 分析结果 ===")
    print(f"总运算数: {summary['total_operations']}")
    print(f"线性运算: {summary['linear_operations']} ({summary['linearity_ratio']:.1%})")
    print(f"非线性运算: {summary['nonlinear_operations']} ({summary['nonlinearity_ratio']:.1%})")
    print(f"未知运算: {summary['unknown_operations']}")
    
    print(f"\n=== 运算符统计 ===")
    for op_type, count in sorted(analysis['operator_statistics'].items()):
        print(f"{op_type:<20}: {count}")
    
    # 生成详细报告
    print("\n3. 生成详细报告...")
    with open("results/correct_linearity_analysis.txt", "w", encoding="utf-8") as f:
        f.write("Intel 4004 ALU 正确线性/非线性分析报告\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("定义说明:\n")
        f.write("- 线性运算: 加法(+), 减法(-), 位移(<<, >>), 位拼接, 位选择等\n")
        f.write("- 非线性运算: 逻辑运算(&, |, ^, ~), 乘法(*), 除法(/), 比较运算等\n\n")
        
        f.write("分析汇总:\n")
        f.write("-" * 15 + "\n")
        f.write(f"总运算数: {summary['total_operations']}\n")
        f.write(f"线性运算: {summary['linear_operations']} ({summary['linearity_ratio']:.1%})\n")
        f.write(f"非线性运算: {summary['nonlinear_operations']} ({summary['nonlinearity_ratio']:.1%})\n")
        f.write(f"未知运算: {summary['unknown_operations']}\n\n")
        
        f.write("运算符详细统计:\n")
        f.write("-" * 20 + "\n")
        for op_type, count in sorted(analysis['operator_statistics'].items()):
            f.write(f"{op_type:<30}: {count}\n")
        
        f.write(f"\n线性运算详情:\n")
        f.write("-" * 15 + "\n")
        for op in analysis['operations']['linear']:
            f.write(f"  {op}\n")
        
        f.write(f"\n非线性运算详情:\n")
        f.write("-" * 18 + "\n")
        for op in analysis['operations']['nonlinear']:
            f.write(f"  {op}\n")
    
    print("   报告已保存到: results/correct_linearity_analysis.txt")

if __name__ == "__main__":
    main()
