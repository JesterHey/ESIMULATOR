#!/usr/bin/env python3
"""
数据流图(DFG)解析器
将DFG文本表示转换为Python数据结构
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
import re


class TermType(Enum):
    INPUT = "Input"
    OUTPUT = "Output"  
    REG = "Reg"
    RENAME = "Rename"


class OperatorType(Enum):
    # 算术运算符
    PLUS = "Plus"
    MINUS = "Minus"
    TIMES = "Times"
    MOD = "Mod"
    
    # 逻辑运算符
    AND = "And"
    OR = "Or"
    XOR = "Xor"
    
    # 比较运算符
    EQ = "Eq"


@dataclass
class IntConst:
    """整数常量"""
    value: str  # 例如: "2'b00", "9'b0", "8", "1"
    
    def __str__(self):
        return f"IntConst({self.value})"


@dataclass
class Terminal:
    """终端节点（变量引用）"""
    name: str
    
    def __str__(self):
        return f"Terminal({self.name})"


@dataclass
class Operator:
    """操作符节点"""
    op_type: OperatorType
    operands: List[Union['Operator', Terminal, IntConst]]
    
    def __str__(self):
        operands_str = ", ".join(str(op) for op in self.operands)
        return f"Operator({self.op_type.value}, [{operands_str}])"


@dataclass
class Branch:
    """分支节点（条件选择）"""
    condition: Union[Operator, Terminal, IntConst]
    true_branch: Union[Operator, Terminal, IntConst]
    false_branch: Optional[Union[Operator, Terminal, IntConst, 'Branch']] = None
    
    def __str__(self):
        return f"Branch(Cond:{self.condition}, True:{self.true_branch}, False:{self.false_branch})"


@dataclass
class Term:
    """项定义"""
    name: str
    types: List[TermType]
    msb: IntConst
    lsb: IntConst
    
    def __str__(self):
        types_str = [t.value for t in self.types]
        return f"Term({self.name}, types={types_str}, width={self.msb.value}:{self.lsb.value})"


@dataclass  
class Bind:
    """绑定关系"""
    dest: str
    tree: Union[Operator, Terminal, IntConst, Branch]
    
    def __str__(self):
        return f"Bind({self.dest} = {self.tree})"


@dataclass
class Instance:
    """实例定义"""
    module_name: str
    instance_name: str
    
    def __str__(self):
        return f"Instance({self.module_name}, {self.instance_name})"


@dataclass
class DFG:
    """完整的数据流图"""
    instance: Optional[Instance] = None
    terms: List[Term] = field(default_factory=list)
    binds: List[Bind] = field(default_factory=list)
    
    def get_term_by_name(self, name: str) -> Optional[Term]:
        """根据名称查找项"""
        for term in self.terms:
            if term.name == name:
                return term
        return None
    
    def get_bind_by_dest(self, dest: str) -> Optional[Bind]:
        """根据目标查找绑定"""
        for bind in self.binds:
            if bind.dest == dest:
                return bind
        return None


class DFGParser:
    """DFG解析器"""
    
    def __init__(self):
        self.current_pos = 0
        self.text = ""
    
    def parse_file(self, filepath: str) -> DFG:
        """解析DFG文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> DFG:
        """解析DFG内容"""
        self.text = content
        self.current_pos = 0
        
        dfg = DFG()
        
        # 按行解析
        lines = content.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别段落
            if line.endswith(':'):
                current_section = line[:-1]
                continue
            
            # 解析不同段落的内容
            if current_section == "Instance":
                instance = self._parse_instance_line(line)
                if instance:
                    dfg.instance = instance
                    
            elif current_section == "Term":
                term = self._parse_term_line(line)
                if term:
                    dfg.terms.append(term)
                    
            elif current_section == "Bind":
                bind = self._parse_bind_line(line)
                if bind:
                    dfg.binds.append(bind)
        
        return dfg
    
    def _parse_instance_line(self, line: str) -> Optional[Instance]:
        """解析实例行"""
        # 匹配格式: (module_name, 'instance_name')
        match = re.match(r'\(([^,]+),\s*[\'"]([^\'\"]+)[\'\"]?\)', line)
        if match:
            return Instance(match.group(1), match.group(2))
        return None
    
    def _parse_term_line(self, line: str) -> Optional[Term]:
        """解析项行"""
        # 匹配格式: (Term name:xxx type:[...] msb:(IntConst x) lsb:(IntConst y))
        pattern = r'\(Term name:([^\s]+) type:\[(.*?)\] msb:\(IntConst ([^\)]+)\) lsb:\(IntConst ([^\)]+)\)\)'
        match = re.match(pattern, line)
        
        if match:
            name = match.group(1)
            types_str = match.group(2)
            msb_val = match.group(3)
            lsb_val = match.group(4)
            
            # 解析类型列表
            types = []
            for type_str in types_str.split(','):
                type_str = type_str.strip().strip("'\"")
                try:
                    types.append(TermType(type_str))
                except ValueError:
                    # 如果枚举中没有这个类型，跳过
                    pass
            
            return Term(
                name=name,
                types=types,
                msb=IntConst(msb_val),
                lsb=IntConst(lsb_val)
            )
        return None
    
    def _parse_bind_line(self, line: str) -> Optional[Bind]:
        """解析绑定行"""
        # 匹配格式: (Bind dest:xxx tree:(...))
        pattern = r'\(Bind dest:([^\s]+) tree:(.*)\)$'
        match = re.match(pattern, line)
        
        if match:
            dest = match.group(1)
            tree_str = match.group(2)
            
            # 解析表达式树
            tree = self._parse_expression(tree_str)
            if tree:
                return Bind(dest=dest, tree=tree)
        
        return None
    
    def _parse_expression(self, expr: str) -> Optional[Union[Operator, Terminal, IntConst, Branch]]:
        """递归解析表达式"""
        expr = expr.strip()
        
        # 解析 IntConst
        if expr.startswith('(IntConst ') or expr.startswith('(IntCon st '):
            # 处理可能的拼写错误
            pattern = r'\(IntCon?st ([^\)]+)\)'
            match = re.match(pattern, expr)
            if match:
                return IntConst(match.group(1))
        
        # 解析 Terminal
        if expr.startswith('(Terminal '):
            pattern = r'\(Terminal ([^\)]+)\)'
            match = re.match(pattern, expr)
            if match:
                return Terminal(match.group(1))
        
        # 解析 Operator
        if expr.startswith('(Operator '):
            return self._parse_operator(expr)
        
        # 解析 Branch
        if expr.startswith('(Branch '):
            return self._parse_branch(expr)
        
        return None
    
    def _parse_operator(self, expr: str) -> Optional[Operator]:
        """解析操作符表达式"""
        # 匹配格式: (Operator OpType Next:((...),(...)))
        pattern = r'\(Operator (\w+) Next:\((.*)\)\)'
        match = re.match(pattern, expr)
        
        if match:
            op_type_str = match.group(1)
            operands_str = match.group(2)
            
            try:
                op_type = OperatorType(op_type_str)
            except ValueError:
                return None
            
            # 解析操作数
            operands = self._parse_operands(operands_str)
            return Operator(op_type=op_type, operands=operands)
        
        return None
    
    def _parse_branch(self, expr: str) -> Optional[Branch]:
        """解析分支表达式"""
        # 这是一个复杂的递归结构，需要仔细解析
        # 匹配格式: (Branch Cond:(...) True:(...) False:(...))
        
        # 找到主要的组成部分
        if not expr.startswith('(Branch '):
            return None
            
        content = expr[8:-1]  # 去掉 "(Branch " 和 ")"
        
        # 使用堆栈方法解析嵌套结构
        parts = self._split_branch_parts(content)
        
        if len(parts) >= 2:
            cond_part = parts.get('Cond')
            true_part = parts.get('True')
            false_part = parts.get('False')
            
            if cond_part and true_part:
                condition = self._parse_expression(cond_part)
                true_branch = self._parse_expression(true_part)
                false_branch = self._parse_expression(false_part) if false_part else None
                
                return Branch(condition=condition, true_branch=true_branch, false_branch=false_branch)
        
        return None
    
    def _split_branch_parts(self, content: str) -> Dict[str, str]:
        """分割分支的各个部分"""
        parts = {}
        current_key = None
        current_value = ""
        paren_count = 0
        i = 0
        
        while i < len(content):
            char = content[i]
            
            # 寻找键
            if char.isalpha() and (i == 0 or content[i-1] == ' '):
                # 可能是新的键
                key_match = re.match(r'(Cond|True|False):', content[i:])
                if key_match:
                    # 保存之前的值
                    if current_key and current_value.strip():
                        parts[current_key] = current_value.strip()
                    
                    # 开始新的键
                    current_key = key_match.group(1)
                    current_value = ""
                    i += len(key_match.group(0))
                    continue
            
            if current_key:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                
                current_value += char
                
                # 如果括号平衡且遇到空格，可能是下一个部分的开始
                if paren_count == 0 and char == ')':
                    # 检查后面是否跟着新的键
                    next_part = content[i+1:].strip()
                    if next_part.startswith('True:') or next_part.startswith('False:'):
                        parts[current_key] = current_value.strip()
                        current_value = ""
                        current_key = None
            
            i += 1
        
        # 保存最后的值
        if current_key and current_value.strip():
            parts[current_key] = current_value.strip()
        
        return parts
    
    def _parse_operands(self, operands_str: str) -> List[Union[Operator, Terminal, IntConst]]:
        """解析操作数列表"""
        operands = []
        
        # 使用括号匹配来分割操作数
        current_operand = ""
        paren_count = 0
        
        i = 0
        while i < len(operands_str):
            char = operands_str[i]
            
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                # 这是分隔符
                if current_operand.strip():
                    operand = self._parse_expression(current_operand.strip())
                    if operand:
                        operands.append(operand)
                current_operand = ""
                i += 1
                continue
            
            current_operand += char
            i += 1
        
        # 处理最后一个操作数
        if current_operand.strip():
            operand = self._parse_expression(current_operand.strip())
            if operand:
                operands.append(operand)
        
        return operands


def pretty_print_dfg(dfg: DFG):
    """美化打印DFG"""
    print("=== 数据流图 (DFG) ===")
    
    if dfg.instance:
        print(f"\n实例: {dfg.instance}")
    
    print(f"\n项定义 ({len(dfg.terms)} 项):")
    for term in dfg.terms:
        print(f"  {term}")
    
    print(f"\n绑定关系 ({len(dfg.binds)} 项):")
    for bind in dfg.binds:
        print(f"  {bind}")


if __name__ == "__main__":
    # 测试解析器
    parser = DFGParser()
    
    try:
        dfg = parser.parse_file("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/alu1_dfg.txt")
        pretty_print_dfg(dfg)
        
        # 示例：访问特定的绑定
        print("\n=== 分析示例 ===")
        result_bind = dfg.get_bind_by_dest("alu1.result")
        if result_bind:
            print(f"输出结果的绑定: {result_bind}")
        
        # 统计输入输出
        inputs = [term for term in dfg.terms if TermType.INPUT in term.types]
        outputs = [term for term in dfg.terms if TermType.OUTPUT in term.types]
        
        print(f"\n输入信号 ({len(inputs)} 个):")
        for inp in inputs:
            print(f"  {inp.name} [{inp.msb.value}:{inp.lsb.value}]")
            
        print(f"\n输出信号 ({len(outputs)} 个):")
        for out in outputs:
            print(f"  {out.name} [{out.msb.value}:{out.lsb.value}]")
            
    except Exception as e:
        print(f"解析错误: {e}")
        import traceback
        traceback.print_exc()
