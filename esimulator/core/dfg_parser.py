#!/usr/bin/env python3
"""
DFG解析器模块
"""

import re
from typing import Dict, List, Optional

class DFGParser:
    """DFG文件解析器"""
    
    def __init__(self):
        self.bind_pattern = r'\(Bind dest:([^\s]+).*?tree:(.*?)\)(?=\n\(Bind|\nBranch:|\n\n|\Z)'
        self.parsed_signals = {}
    
    def parse_file(self, file_path: str) -> Dict:
        """解析DFG文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> Dict:
        """解析DFG内容"""
        matches = list(re.finditer(self.bind_pattern, content, re.DOTALL))
        
        signals = {}
        for match in matches:
            signal_name = match.group(1)
            tree_expr = match.group(2).strip()
            signals[signal_name] = tree_expr
        
        self.parsed_signals = signals
        
        return {
            'total_signals': len(signals),
            'signals': signals
        }
    
    def get_signal_expression(self, signal_name: str) -> Optional[str]:
        """获取指定信号的表达式"""
        return self.parsed_signals.get(signal_name)
    
    def list_signals(self) -> List[str]:
        """列出所有信号名称"""
        return list(self.parsed_signals.keys())
    
    def extract_operators(self, expression: str) -> List[str]:
        """从表达式中提取运算符"""
        operator_pattern = r'\(Operator (\w+) Next:'
        return re.findall(operator_pattern, expression)
    
    def get_expression_type(self, expression: str) -> str:
        """获取表达式类型"""
        if expression.startswith('(Terminal '):
            return 'terminal'
        elif expression.startswith('(IntConst '):
            return 'constant'
        elif expression.startswith('(Branch '):
            return 'branch'
        elif expression.startswith('(Concat '):
            return 'concat'
        elif expression.startswith('(Operator '):
            return 'operator'
        else:
            return 'unknown'
