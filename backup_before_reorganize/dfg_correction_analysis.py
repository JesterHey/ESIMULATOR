#!/usr/bin/env python3
"""
DFG表达式分析和修正方案
基于实际的4004 DFG文件内容设计正确的线性分析方法
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional, Union
import json

@dataclass
class ExpressionNode:
    """表达式树节点"""
    node_type: str  # 'operator', 'terminal', 'constant', 'branch', 'concat', 'partselect'
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

class CorrectedLinearityAnalyzer:
    """修正的线性分析器"""
    
    def __init__(self):
        # 严格的线性运算符定义
        self.linear_operators = {
            'Plus', 'Minus', 'UnaryMinus',  # 基本算术运算
            'Concat', 'Partselect'          # 位操作（线性组合）
        }
        
        # 非线性运算符
        self.nonlinear_operators = {
            'And', 'Or', 'Xor', 'Xnor',     # 逻辑运算
            'Unot', 'Unor', 'Uand', 'Uxor', # 归约运算
            'Times', 'Divide', 'Mod',       # 乘除运算
            'Eq', 'NotEq', 'Lt', 'Gt', 'Lte', 'Gte',  # 比较运算
            'Sll', 'Srl'                    # 位移运算（重新分类为非线性）
        }
        
        self.signal_analyses = {}
        self.total_expressions = 0
    
    def analyze_dfg_file(self, file_path: str) -> Dict:
        """分析DFG文件，按表达式级别进行线性分析"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("=== 修正的DFG线性分析 ===")
        print("修正策略:")
        print("1. 按信号表达式分析，而非单个运算符")
        print("2. 递归解析表达式树结构")
        print("3. 整体判断表达式线性特征")
        print("4. 重新分类位移运算为非线性\n")
        
        # 提取所有Bind表达式
        bind_pattern = r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
        matches = list(re.finditer(bind_pattern, content, re.DOTALL))
        
        self.total_expressions = len(matches)
        print(f"找到 {self.total_expressions} 个信号表达式")
        
        # 分析每个表达式
        for match in matches:
            signal_name = match.group(1)
            tree_expr = match.group(2).strip()
            
            try:
                analysis = self._analyze_signal_expression(signal_name, tree_expr)
                self.signal_analyses[signal_name] = analysis
            except Exception as e:
                print(f"分析信号 {signal_name} 时出错: {e}")
                # 默认标记为非线性
                self.signal_analyses[signal_name] = {
                    'is_linear': False,
                    'reason': f'解析错误: {str(e)}',
                    'complexity': 'error',
                    'operators': []
                }
        
        return self._generate_comprehensive_report()
    
    def _analyze_signal_expression(self, signal_name: str, tree_expr: str) -> Dict:
        """分析单个信号表达式"""
        
        # 检测表达式类型
        if tree_expr.startswith('(Terminal '):
            # 直接终端赋值 - 线性
            return {
                'is_linear': True,
                'reason': '直接终端赋值',
                'complexity': 'simple',
                'operators': [],
                'expression_type': 'terminal'
            }
        
        elif tree_expr.startswith('(IntConst '):
            # 常量赋值 - 线性
            return {
                'is_linear': True,
                'reason': '常量赋值',
                'complexity': 'simple', 
                'operators': [],
                'expression_type': 'constant'
            }
        
        elif tree_expr.startswith('(Branch '):
            # 分支表达式 - 通常非线性
            return self._analyze_branch_expression(tree_expr)
        
        elif tree_expr.startswith('(Concat '):
            # 拼接表达式 - 需要检查子表达式
            return self._analyze_concat_expression(tree_expr)
        
        elif tree_expr.startswith('(Operator '):
            # 运算符表达式 - 递归分析
            return self._analyze_operator_expression(tree_expr)
        
        else:
            # 未知类型
            return {
                'is_linear': False,
                'reason': f'未识别的表达式类型: {tree_expr[:50]}...',
                'complexity': 'unknown',
                'operators': [],
                'expression_type': 'unknown'
            }
    
    def _analyze_operator_expression(self, expr: str) -> Dict:
        """分析运算符表达式"""
        
        operators_found = []
        is_linear = True
        nonlinear_reason = None
        
        # 提取所有运算符
        operator_pattern = r'\(Operator (\w+) Next:'
        matches = list(re.finditer(operator_pattern, expr))
        
        for match in matches:
            operator = match.group(1)
            operators_found.append(operator)
            
            if operator in self.nonlinear_operators:
                is_linear = False
                if nonlinear_reason is None:
                    nonlinear_reason = f'包含非线性运算符: {operator}'
        
        # 检查是否包含Branch（条件分支）
        if '(Branch ' in expr:
            is_linear = False
            if nonlinear_reason is None:
                nonlinear_reason = '包含条件分支'
        
        # 确定复杂度
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
        """分析分支表达式"""
        
        # 分支表达式本质上是非线性的（多项式逻辑）
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
        """分析拼接表达式"""
        
        # 拼接本身是线性的，但需要检查子表达式
        operator_pattern = r'\(Operator (\w+) Next:'
        operators = re.findall(operator_pattern, expr)
        
        # 如果包含非线性运算符，整体非线性
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
        
        # 统计线性/非线性表达式
        linear_count = sum(1 for analysis in self.signal_analyses.values() 
                          if analysis['is_linear'])
        nonlinear_count = self.total_expressions - linear_count
        
        # 按复杂度分类
        complexity_stats = defaultdict(int)
        expression_type_stats = defaultdict(int)
        
        # 统计各类非线性原因
        nonlinear_reasons = defaultdict(int)
        
        for signal, analysis in self.signal_analyses.items():
            complexity_stats[analysis['complexity']] += 1
            expression_type_stats[analysis['expression_type']] += 1
            
            if not analysis['is_linear']:
                reason = analysis['reason'].split(':')[0] if ':' in analysis['reason'] else analysis['reason']
                nonlinear_reasons[reason] += 1
        
        # 运算符使用统计
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

def demonstrate_correction():
    """演示修正方案"""
    
    print("=== DFG表达式线性分析修正方案演示 ===\n")
    
    # 测试几个具体的表达式
    test_cases = [
        {
            'name': 'alu._rn1_dout',
            'expr': '(Terminal alu.acc_out)',
            'expected': '线性（直接终端赋值）'
        },
        {
            'name': 'alu.acb_ib', 
            'expr': '(Operator Unot Next:(Operator And Next:(Operator Or Next:(Terminal alu.x31_clk2),(Operator Unot Next:(Terminal alu.xch))),(Operator Or Next:(Terminal alu.x21_clk2),(Operator Unot Next:(Terminal alu.iow)))))',
            'expected': '非线性（包含逻辑运算）'
        },
        {
            'name': 'alu._rn4_dout',
            'expr': '(Concat Next:(Terminal alu.n0358),(Terminal alu.n0366),(Terminal alu.n0359),(Terminal alu.n0357))',
            'expected': '线性（纯拼接，无运算符）'
        }
    ]
    
    analyzer = CorrectedLinearityAnalyzer()
    
    print("个别表达式测试:")
    print("-" * 50)
    
    for test in test_cases:
        analysis = analyzer._analyze_signal_expression(test['name'], test['expr'])
        result = "线性" if analysis['is_linear'] else "非线性"
        
        print(f"信号: {test['name']}")
        print(f"表达式: {test['expr'][:60]}...")
        print(f"分析结果: {result}")
        print(f"原因: {analysis['reason']}")
        print(f"预期结果: {test['expected']}")
        print(f"是否正确: {'✓' if (result in test['expected']) else '✗'}")
        print()

def analyze_real_dfg():
    """分析真实的DFG文件"""
    
    print("=== 真实4004 ALU DFG分析 ===\n")
    
    analyzer = CorrectedLinearityAnalyzer()
    dfg_file = "/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/4004_dfg.txt"
    
    # 分析DFG文件
    report = analyzer.analyze_dfg_file(dfg_file)
    
    print(f"\n=== 修正后的分析结果 ===")
    summary = report['summary']
    print(f"总表达式数: {summary['total_expressions']}")
    print(f"线性表达式: {summary['linear_expressions']} ({summary['linearity_ratio']:.1%})")
    print(f"非线性表达式: {summary['nonlinear_expressions']} ({1-summary['linearity_ratio']:.1%})")
    
    print(f"\n表达式类型分布:")
    for expr_type, count in report['expression_type_distribution'].items():
        percentage = count / summary['total_expressions'] * 100
        print(f"  {expr_type}: {count} ({percentage:.1f}%)")
    
    print(f"\n复杂度分布:")
    for complexity, count in report['complexity_distribution'].items():
        percentage = count / summary['total_expressions'] * 100
        print(f"  {complexity}: {count} ({percentage:.1f}%)")
    
    print(f"\n非线性原因分析:")
    for reason, count in report['nonlinear_reasons'].items():
        print(f"  {reason}: {count}")
    
    print(f"\n运算符使用统计（前10位）:")
    sorted_ops = sorted(report['operator_usage'].items(), key=lambda x: x[1], reverse=True)
    for op, count in sorted_ops[:10]:
        op_type = "线性" if op in analyzer.linear_operators else "非线性"
        print(f"  {op} ({op_type}): {count}")
    
    # 生成修正报告
    print(f"\n3. 生成修正报告...")
    with open("results/corrected_linearity_analysis.txt", "w", encoding="utf-8") as f:
        f.write("Intel 4004 ALU 修正线性分析报告\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("修正要点:\n")
        f.write("1. 按信号表达式分析，而非单个运算符统计\n")
        f.write("2. 位移运算重新分类为非线性\n")
        f.write("3. 考虑表达式树的整体结构\n")
        f.write("4. 区分不同类型的表达式\n\n")
        
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
    
    print("   修正报告已保存到: results/corrected_linearity_analysis.txt")

if __name__ == "__main__":
    demonstrate_correction()
    print("\n" + "="*60 + "\n")
    analyze_real_dfg()
