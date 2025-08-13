# ESIMULATOR 现场演示脚本

## 🎯 演示目标
展示ESIMULATOR对Intel 4004 ALU的DFG线性度分析技术

## 📋 演示流程 (5分钟)

### 演示1：线性度分析 (2分钟)
```bash
# 运行核心分析器
python src/analyzers/correct_linearity_analyzer.py
```

**预期输出展示：**
```
Intel 4004 ALU DFG线性度分析
================================
总信号数: 58个主要信号  
运算操作: 465个运算操作
线性运算: 294个 (63.2%)
非线性运算: 171个 (36.8%)

线性运算类型：
- 加法运算: +
- 减法运算: -  
- 位移运算: <<, >>
- 位操作: 拼接, 选择
- 直接赋值: =

非线性运算类型：
- 逻辑运算: &, |, ^, ~
- 比较运算: ==, !=, <, >
- 乘除运算: *, /
================================
```

### 演示2：DAG结构分析 (2分钟)
```bash
# 运行DAG结构分析器
python src/dag_structure_analyzer.py
```

**预期输出展示：**
```
DFG到DAG结构分析
=================
节点统计:
- 信号节点: 58个
- 运算节点: 465个
- 连接关系: 182个

拓扑分析:
- 最大深度: 12层
- 关键路径: 8条
- 环路检测: 已处理

层次分布:
第1层: 输入信号 (8个)
第2层: 基础运算 (15个)  
第3层: 中间结果 (20个)
...
第12层: 输出信号 (4个)
=================
```

### 演示3：项目文档结构 (1分钟)
```bash
# 显示项目结构
tree -I '__pycache__|*.pyc' -L 3
```

**预期输出展示：**
```
ESIMULATOR/
├── src/
│   ├── analyzers/
│   │   ├── correct_linearity_analyzer.py
│   │   └── signal_connection_analyzer.py
│   ├── dag_structure_analyzer.py
│   └── utils/
├── dfg_files/
│   └── alu1_dfg.txt
├── results/
│   ├── reports/
│   ├── data/
│   └── visualizations/
├── docs/
└── demo.py
```

## 🔧 技术解释要点

### 线性/非线性定义
```python
# 核心判断逻辑
def is_linear_operator(op):
    linear_ops = {'+', '-', '<<', '>>', 'concat', 'select', '='}
    return op in linear_ops

def is_nonlinear_operator(op):  
    nonlinear_ops = {'&', '|', '^', '~', '*', '/', '==', '!=', '<', '>'}
    return op in nonlinear_ops
```

### 表达式级别分析
```python
# 分析完整表达式
def analyze_expression(expr_string):
    operators = parse_operators(expr_string)
    
    # 一票否决制：任何非线性运算符 → 整个表达式非线性
    for op in operators:
        if is_nonlinear_operator(op):
            return "非线性"
    
    return "线性"
```

### DAG处理算法
```python
# 环路友好的拓扑排序
def topological_sort_with_cycles(graph):
    # 使用改进的Kahn算法
    # 支持弱连通分量分析
    # 处理反馈边
    pass
```

## 💡 现场讲解重点

### 1. 技术原理强调 (30秒)
- "我们基于数学严格定义进行表达式级别分析"
- "线性函数定义：f(ax + by) = af(x) + bf(y)"
- "一票否决制：任何非线性运算符使整个表达式非线性"

### 2. 分析结果解释 (60秒)
- "465个运算操作中294个是线性的"
- "这符合ALU中算术运算较多的特点"
- "182个连接关系形成复杂的数据流网络"

### 3. 技术实现亮点 (30秒)
- "环路友好的图分析算法"
- "模块化的分析器设计"
- "多格式输出支持"

### 4. 应用价值说明 (60秒)
- "为数字电路设计提供准确的信号特征分析"
- "支持性能优化和功耗建模"
- "为EDA工具开发提供理论基础"

## ⚠️ 演示注意事项

### 环境准备
- 确保所有Python脚本可以正常运行
- 准备好结果文件的备份版本
- 测试命令执行时间（避免过长等待）

### 故障预案
- 如果脚本运行失败，准备静态结果文件展示
- 准备核心代码片段的截图
- 准备项目结构的图片版本

### 时间控制
- 每个演示环节严格控制在指定时间内
- 如果输出过长，使用 `| head -20` 限制显示行数
- 准备快速跳过不重要输出的方法

## 🎯 演示成功标准

观众应该在5分钟内理解：
1. ✅ 项目是做什么的（DFG线性度分析）
2. ✅ 技术方法是什么（表达式级别分析）
3. ✅ 分析结果是什么（294/465线性运算）
4. ✅ 项目价值是什么（电路设计理论基础）

**关键信息：技术严谨、结果准确、应用实用**
