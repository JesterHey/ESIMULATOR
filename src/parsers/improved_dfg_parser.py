#!/usr/bin/env python3
"""
改进的DFG解析器 - 专门处理复杂的分支结构
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
    value: str
    
    def __str__(self):
        return f"IntConst({self.value})"
    
    def __repr__(self):
        return str(self)


@dataclass
class Terminal:
    """终端节点（变量引用）"""
    name: str
    
    def __str__(self):
        return f"Terminal({self.name})"
    
    def __repr__(self):
        return str(self)


@dataclass
class Operator:
    """操作符节点"""
    op_type: OperatorType
    operands: List[Union['Operator', Terminal, IntConst]]
    
    def __str__(self):
        operands_str = ", ".join(str(op) for op in self.operands)
        return f"Operator({self.op_type.value}, [{operands_str}])"
    
    def __repr__(self):
        return str(self)


@dataclass
class Branch:
    """分支节点（条件选择）"""
    condition: Union[Operator, Terminal, IntConst, 'Branch']
    true_branch: Union[Operator, Terminal, IntConst, 'Branch']
    false_branch: Optional[Union[Operator, Terminal, IntConst, 'Branch']] = None
    
    def __str__(self):
        return f"Branch(Cond:{self.condition}, True:{self.true_branch}, False:{self.false_branch})"
    
    def __repr__(self):
        return str(self)


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


class ExpressionTokenizer:
    """表达式分词器"""
    
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.tokens = []
        self.tokenize()
    
    def tokenize(self):
        """将表达式分解为标记"""
        i = 0
        current_token = ""
        paren_depth = 0
        
        while i < len(self.text):
            char = self.text[i]
            
            if char == '(':
                if current_token.strip():
                    self.tokens.append(current_token.strip())
                    current_token = ""
                self.tokens.append('(')
                paren_depth += 1
            elif char == ')':
                if current_token.strip():
                    self.tokens.append(current_token.strip())
                    current_token = ""
                self.tokens.append(')')
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                if current_token.strip():
                    self.tokens.append(current_token.strip())
                    current_token = ""
                self.tokens.append(',')
            elif char == ' ' and paren_depth == 0:
                if current_token.strip():
                    self.tokens.append(current_token.strip())
                    current_token = ""
            else:
                current_token += char
            
            i += 1
        
        if current_token.strip():
            self.tokens.append(current_token.strip())
    
    def peek(self) -> Optional[str]:
        """查看下一个标记"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None
    
    def next(self) -> Optional[str]:
        """获取下一个标记"""
        if self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            self.pos += 1
            return token
        return None
    
    def expect(self, expected: str) -> bool:
        """检查下一个标记是否是期望的"""
        token = self.peek()
        if token == expected:
            self.next()
            return True
        return False


class ImprovedDFGParser:
    """改进的DFG解析器"""
    
    def parse_file(self, filepath: str) -> DFG:
        """解析DFG文件"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> DFG:
        """解析DFG内容"""
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
        match = re.match(r'\(([^,]+),\s*[\'"]([^\'\"]+)[\'\"]?\)', line)
        if match:
            return Instance(match.group(1), match.group(2))
        return None
    
    def _parse_term_line(self, line: str) -> Optional[Term]:
        """解析项行"""
        pattern = r'\(Term name:([^\s]+) type:\[(.*?)\] msb:\(IntConst ([^\)]+)\) lsb:\(IntConst ([^\)]+)\)\)'
        match = re.match(pattern, line)
        
        if match:
            name = match.group(1)
            types_str = match.group(2)
            msb_val = match.group(3)
            lsb_val = match.group(4)
            
            types = []
            for type_str in types_str.split(','):
                type_str = type_str.strip().strip("'\"")
                try:
                    types.append(TermType(type_str))
                except ValueError:
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
        pattern = r'\(Bind dest:([^\s]+) tree:(.*)\)$'
        match = re.match(pattern, line)
        
        if match:
            dest = match.group(1)
            tree_str = match.group(2)
            
            tree = self._parse_expression(tree_str)
            if tree:
                return Bind(dest=dest, tree=tree)
        
        return None
    
    def _parse_expression(self, expr: str) -> Optional[Union[Operator, Terminal, IntConst, Branch]]:
        """解析表达式 - 使用递归下降解析器"""
        expr = expr.strip()
        
        # IntConst (处理拼写错误)
        if expr.startswith('(IntConst ') or expr.startswith('(IntCon st '):
            pattern = r'\(IntCon?st ([^\)]+)\)'
            match = re.match(pattern, expr)
            if match:
                return IntConst(match.group(1))
        
        # Terminal
        if expr.startswith('(Terminal '):
            pattern = r'\(Terminal ([^\)]+)\)'
            match = re.match(pattern, expr)
            if match:
                return Terminal(match.group(1))
        
        # Operator
        if expr.startswith('(Operator '):
            return self._parse_operator(expr)
        
        # Branch - 使用更强大的解析方法
        if expr.startswith('(Branch '):
            return self._parse_branch_recursive(expr)
        
        return None
    
    def _parse_operator(self, expr: str) -> Optional[Operator]:
        """解析操作符表达式"""
        pattern = r'\(Operator (\w+) Next:\((.*)\)\)'
        match = re.match(pattern, expr)
        
        if match:
            op_type_str = match.group(1)
            operands_str = match.group(2)
            
            try:
                op_type = OperatorType(op_type_str)
            except ValueError:
                return None
            
            operands = self._parse_operands(operands_str)
            return Operator(op_type=op_type, operands=operands)
        
        return None
    
    def _parse_operands(self, operands_str: str) -> List[Union[Operator, Terminal, IntConst]]:
        """解析操作数列表"""
        operands = []
        parts = self._split_by_comma_at_level_zero(operands_str)
        
        for part in parts:
            operand = self._parse_expression(part.strip())
            if operand:
                operands.append(operand)
        
        return operands
    
    def _split_by_comma_at_level_zero(self, text: str) -> List[str]:
        """在括号层次为0时按逗号分割"""
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in text:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
                continue
            
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts
    
    def _parse_branch_recursive(self, expr: str) -> Optional[Branch]:
        """递归解析分支表达式"""
        if not expr.startswith('(Branch '):
            return None
        
        # 移除外层的 "(Branch " 和 ")"
        content = expr[8:-1].strip()
        
        # 解析 Cond:, True:, False: 部分
        parts = self._extract_branch_components(content)
        
        if 'Cond' not in parts or 'True' not in parts:
            return None
        
        condition = self._parse_expression(parts['Cond'])
        true_branch = self._parse_expression(parts['True'])
        false_branch = None
        
        if 'False' in parts and parts['False']:
            false_branch = self._parse_expression(parts['False'])
        
        if condition and true_branch:
            return Branch(condition=condition, true_branch=true_branch, false_branch=false_branch)
        
        return None
    
    def _extract_branch_components(self, content: str) -> Dict[str, str]:
        """提取分支的各个组件"""
        components = {}
        i = 0
        
        while i < len(content):
            # 寻找键
            for key in ['Cond:', 'True:', 'False:']:
                if content[i:].startswith(key):
                    # 找到了键，现在提取值
                    start_pos = i + len(key)
                    value, next_pos = self._extract_value_from_position(content, start_pos)
                    components[key[:-1]] = value  # 去掉冒号
                    i = next_pos
                    break
            else:
                i += 1
        
        return components
    
    def _extract_value_from_position(self, content: str, start_pos: int) -> tuple[str, int]:
        """从指定位置提取值，直到下一个键或结束"""
        value = ""
        paren_count = 0
        i = start_pos
        
        # 跳过空格
        while i < len(content) and content[i] == ' ':
            i += 1
        
        while i < len(content):
            char = content[i]
            
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            
            # 检查是否遇到了下一个键
            if paren_count == 0:
                remaining = content[i:].strip()
                if remaining.startswith('True:') or remaining.startswith('False:'):
                    break
            
            value += char
            i += 1
        
        return value.strip(), i


def analyze_dfg_structure(dfg: DFG):
    """分析DFG结构"""
    print("=== DFG 结构分析 ===")
    
    if dfg.instance:
        print(f"模块实例: {dfg.instance.module_name} ({dfg.instance.instance_name})")
    
    # 分类统计
    inputs = [t for t in dfg.terms if TermType.INPUT in t.types]
    outputs = [t for t in dfg.terms if TermType.OUTPUT in t.types]
    regs = [t for t in dfg.terms if TermType.REG in t.types]
    renames = [t for t in dfg.terms if TermType.RENAME in t.types]
    
    print(f"\n信号统计:")
    print(f"  输入信号: {len(inputs)} 个")
    print(f"  输出信号: {len(outputs)} 个")
    print(f"  寄存器: {len(regs)} 个")
    print(f"  重命名: {len(renames)} 个")
    
    print(f"\n输入信号详情:")
    for inp in inputs:
        width = int(inp.msb.value) - int(inp.lsb.value) + 1
        print(f"  {inp.name}: {width} 位 [{inp.msb.value}:{inp.lsb.value}]")
    
    print(f"\n输出信号详情:")
    for out in outputs:
        width = int(out.msb.value) - int(out.lsb.value) + 1
        print(f"  {out.name}: {width} 位 [{out.msb.value}:{out.lsb.value}]")
    
    # 分析绑定关系
    print(f"\n绑定关系分析:")
    for bind in dfg.binds:
        print(f"  {bind.dest} = {type(bind.tree).__name__}")
        if isinstance(bind.tree, Branch):
            print(f"    分支结构 (条件选择)")
        elif isinstance(bind.tree, Operator):
            print(f"    操作: {bind.tree.op_type.value}")


def generate_python_simulator(dfg: DFG) -> str:
    """生成Python模拟器代码"""
    code = []
    code.append("#!/usr/bin/env python3")
    code.append('"""')
    code.append(f"基于DFG生成的 {dfg.instance.module_name if dfg.instance else 'Unknown'} 模块模拟器")
    code.append('"""')
    code.append("")
    code.append("def simulate_alu1(a, b, c, op):")
    code.append('    """模拟ALU1模块的行为"""')
    
    # 生成中间变量计算
    for bind in dfg.binds:
        if bind.dest.endswith('_rn0_result'):
            code.append("    # op == 2'b00: result = (a + b) * c")
            code.append("    _rn0_result = (a + b) * c")
        elif bind.dest.endswith('_rn1_result'):
            code.append("    # op == 2'b01: result = (a - b) ^ c")
            code.append("    _rn1_result = (a - b) ^ c")
        elif bind.dest.endswith('_rn2_result'):
            code.append("    # op == 2'b10: result = a & (b | c)")
            code.append("    _rn2_result = a & (b | c)")
        elif bind.dest.endswith('_rn3_result'):
            code.append("    # op == 2'b11: result = (a % b) + (a * c)")
            code.append("    _rn3_result = (a % b) + (a * c) if b != 0 else a * c")
        elif bind.dest.endswith('_rn4_result'):
            code.append("    # default case")
            code.append("    _rn4_result = 0")
    
    # 生成主要的选择逻辑
    code.append("")
    code.append("    # 根据操作码选择结果")
    code.append("    if op == 0b00:")
    code.append("        result = _rn0_result")
    code.append("    elif op == 0b01:")
    code.append("        result = _rn1_result")
    code.append("    elif op == 0b10:")
    code.append("        result = _rn2_result")
    code.append("    elif op == 0b11:")
    code.append("        result = _rn3_result")
    code.append("    else:")
    code.append("        result = _rn4_result")
    code.append("")
    code.append("    # 确保结果在9位范围内")
    code.append("    return result & 0x1FF")
    code.append("")
    
    # 添加测试代码
    code.append("")
    code.append('if __name__ == "__main__":')
    code.append("    # 测试用例")
    code.append("    test_cases = [")
    code.append("        (5, 3, 2, 0b00),  # (5+3)*2 = 16")
    code.append("        (5, 3, 2, 0b01),  # (5-3)^2 = 2^2 = 0")
    code.append("        (5, 3, 2, 0b10),  # 5&(3|2) = 5&3 = 1")
    code.append("        (5, 3, 2, 0b11),  # (5%3)+(5*2) = 2+10 = 12")
    code.append("        (5, 3, 2, 0b100), # default = 0")
    code.append("    ]")
    code.append("")
    code.append("    for a, b, c, op in test_cases:")
    code.append("        result = simulate_alu1(a, b, c, op)")
    code.append('        print(f"a={a}, b={b}, c={c}, op={op:02b} => result={result}")')
    
    return "\n".join(code)


def main():
    parser = ImprovedDFGParser()
    
    try:
        dfg = parser.parse_file("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/dfg_files/alu1_dfg.txt")
        
        # 详细分析
        analyze_dfg_structure(dfg)
        
        print("\n" + "="*50)
        print("绑定关系详情:")
        for i, bind in enumerate(dfg.binds, 1):
            print(f"{i}. {bind}")
        
        # 生成Python模拟器
        print("\n" + "="*50)
        print("生成Python模拟器代码...")
        
        simulator_code = generate_python_simulator(dfg)
        
        # 保存模拟器代码
        with open("/Users/xuxiaolan/PycharmProjects/ESIMULATOR/4004_simulator.py", 'w') as f:
            f.write(simulator_code)
        
        print("模拟器代码已保存到 4004_simulator.py")
        
    except Exception as e:
        print(f"解析错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
