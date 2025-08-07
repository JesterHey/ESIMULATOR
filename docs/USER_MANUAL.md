# 🚀 ESIMULATOR 使用手册

## 📖 快速入门指南

### 1. 基本使用

**运行主要分析工具**：

```bash
cd /Users/xuxiaolan/PycharmProjects/ESIMULATOR
python analyze_linearity.py
```

**查看分析结果**：

```bash
# 查看修正后的正确分析结果（推荐）
cat results/corrected_linearity_analysis.txt

# 查看原始错误分析结果（仅供对比）
cat results/correct_linearity_analysis.txt
```

**运行对比演示**：

```bash
python demo_comparison.py
```

### 2. 核心工作流程

```mermaid
graph LR
    A[DFG文件] --> B[analyze_linearity.py]
    B --> C[CorrectedLinearityAnalyzer]
    C --> D[表达式分析]
    D --> E[生成报告]
    E --> F[results/目录]
```

### 3. 模块导入使用

如果需要在自己的代码中使用分析功能：

```python
#!/usr/bin/env python3
import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 导入修正的线性分析器
from analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer

def custom_analysis():
    # 创建分析器实例
    analyzer = CorrectedLinearityAnalyzer()
    
    # 分析DFG文件
    report = analyzer.analyze_dfg_file("dfg_files/4004_dfg.txt")
    
    # 获取分析摘要
    summary = report['summary']
    print(f"线性度: {summary['linearity_ratio']:.1%}")
    print(f"线性信号: {summary['linear_expressions']}")
    print(f"非线性信号: {summary['nonlinear_expressions']}")
    
    return report

if __name__ == "__main__":
    custom_analysis()
```

## 🎯 模块功能说明

### 核心分析模块

#### **CorrectedLinearityAnalyzer** (推荐使用)

**位置**: `src/analyzers/dfg_linearity_corrector.py`

**主要方法**:

- `analyze_dfg_file(file_path)` - 分析DFG文件
- `_analyze_signal_expression(signal_name, tree_expr)` - 分析单个信号表达式
- `_analyze_operator_expression(expr)` - 分析运算符表达式
- `_analyze_branch_expression(expr)` - 分析分支表达式
- `_analyze_concat_expression(expr)` - 分析拼接表达式

**使用示例**:

```python
from analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer

analyzer = CorrectedLinearityAnalyzer()
report = analyzer.analyze_dfg_file("dfg_files/4004_dfg.txt")

# 获取线性度
linearity = report['summary']['linearity_ratio']
print(f"线性度: {linearity:.1%}")
```

### 辅助工具模块

#### **AnalysisComparator**

**位置**: `src/analyzers/analysis_comparator.py`

**功能**: 对比不同分析方法的结果

```python
from analyzers.analysis_comparator import compare_analysis_methods

# 执行方法对比
compare_analysis_methods()
```

#### **SignalConnectionAnalyzer**

**位置**: `src/analyzers/signal_connection_analyzer.py`

**功能**: 分析信号连接关系

```python
from analyzers.signal_connection_analyzer import SignalConnectionAnalyzer

analyzer = SignalConnectionAnalyzer()
connections = analyzer.analyze_connections("dfg_files/4004_dfg.txt")
```

## 📊 输出结果解读

### 分析报告结构

**主要输出文件**: `results/corrected_linearity_analysis.txt`

**报告内容包括**:

1. **分析摘要**
   - 总表达式数
   - 线性表达式数量和比例
   - 非线性表达式数量和比例

2. **表达式类型分布**
   - terminal: 直接终端赋值
   - constant: 常量赋值
   - operator: 运算符表达式
   - branch: 分支表达式
   - concat: 拼接表达式

3. **复杂度分布**
   - simple: 简单表达式（≤1个运算符）
   - moderate: 中等复杂度（2-5个运算符）
   - complex: 复杂表达式（>5个运算符）

4. **非线性原因分析**
   - 包含非线性运算符
   - 条件分支表达式
   - 拼接中包含非线性子表达式

5. **详细信号分析**
   - 每个信号的线性/非线性判断
   - 具体原因说明

### 典型分析结果示例

```text
Intel 4004 ALU 修正线性分析报告
===============================================

分析结果:
---------------
总表达式数: 80
线性表达式: 13 (16.2%)
非线性表达式: 67 (83.8%)

表达式类型分布:
--------------------
operator        :  64 ( 80.0%)
terminal        :  13 ( 16.2%)
branch          :   2 (  2.5%)
concat          :   1 (  1.2%)

详细信号分析:
--------------------
alu._rn0_dout       : 线性     - 常量赋值
alu._rn1_dout       : 线性     - 直接终端赋值
alu.acb_ib          : 非线性    - 包含非线性运算符: Unot
alu.acc             : 非线性    - 条件分支表达式（本质非线性）
...
```

## 🔧 定制化使用

### 自定义分析规则

如果需要修改线性/非线性运算符的定义：

```python
from analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer

# 创建分析器实例
analyzer = CorrectedLinearityAnalyzer()

# 自定义线性运算符
analyzer.linear_operators = {
    'Plus', 'Minus', 'UnaryMinus',  # 保持基本算术运算
    'Concat', 'Partselect',         # 保持位操作
    'Sll', 'Srl'                    # 如果要将位移重新分类为线性
}

# 自定义非线性运算符
analyzer.nonlinear_operators = {
    'And', 'Or', 'Xor', 'Xnor',     # 逻辑运算
    'Unot', 'Unor', 'Uand', 'Uxor', # 归约运算
    'Times', 'Divide', 'Mod',       # 乘除运算
    'Eq', 'NotEq', 'Lt', 'Gt', 'Lte', 'Gte'  # 比较运算
}

# 执行分析
report = analyzer.analyze_dfg_file("dfg_files/4004_dfg.txt")
```

### 批量分析多个文件

```python
import os
from analyzers.dfg_linearity_corrector import CorrectedLinearityAnalyzer

def batch_analysis():
    analyzer = CorrectedLinearityAnalyzer()
    dfg_dir = "dfg_files/"
    
    for filename in os.listdir(dfg_dir):
        if filename.endswith('.txt'):
            file_path = os.path.join(dfg_dir, filename)
            print(f"\n分析文件: {filename}")
            
            report = analyzer.analyze_dfg_file(file_path)
            summary = report['summary']
            
            print(f"线性度: {summary['linearity_ratio']:.1%}")
            print(f"总信号: {summary['total_expressions']}")

if __name__ == "__main__":
    batch_analysis()
```

## ⚠️ 注意事项

### 重要提醒

1. **使用正确的分析器**
   - ✅ 使用 `CorrectedLinearityAnalyzer`（修正版）
   - ❌ 避免使用 `CorrectLinearityAnalyzer`（有缺陷的版本）

2. **查看正确的结果文件**
   - ✅ 查看 `results/corrected_linearity_analysis.txt`（修正结果）
   - ❌ 避免依赖 `results/correct_linearity_analysis.txt`（错误结果）

3. **理解分析级别**
   - ✅ 表达式级别分析（整体判断）
   - ❌ 运算符级别统计（局部统计）

### 常见问题

**Q: 为什么两个分析结果差异这么大？**

A: 原始方法按运算符个数统计（294个+/-运算符 vs 171个逻辑运算符），修正方法按表达式整体特征判断（一个表达式即使有100个+号，只要有1个&号就是非线性）。

**Q: 位移运算为什么被分类为非线性？**

A: 位移操作 `x << n` 数学上等价于 `x × 2ⁿ`，本质是乘法运算，不满足线性性质 `f(ax + by) = af(x) + bf(y)`。

**Q: 如何验证分析结果的正确性？**

A: 可以使用 `demo_comparison.py` 查看修正前后的对比，以及具体的表达式分析过程。

## 📈 性能优化

### 大文件处理

对于大型DFG文件，可以考虑以下优化：

```python
def analyze_large_dfg(file_path, chunk_size=1000):
    """分块处理大型DFG文件"""
    analyzer = CorrectedLinearityAnalyzer()
    
    # 可以实现分块读取和处理逻辑
    # 这里是示例框架
    
    return analyzer.analyze_dfg_file(file_path)
```

### 并行处理

对于多文件批量处理：

```python
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def parallel_analysis(file_list):
    """并行分析多个DFG文件"""
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        results = executor.map(analyze_single_file, file_list)
    return list(results)

def analyze_single_file(file_path):
    analyzer = CorrectedLinearityAnalyzer()
    return analyzer.analyze_dfg_file(file_path)
```

## 🤝 扩展开发

### 添加新的分析功能

如果需要添加新的分析维度：

```python
class ExtendedLinearityAnalyzer(CorrectedLinearityAnalyzer):
    """扩展的线性分析器"""
    
    def __init__(self):
        super().__init__()
        # 添加新的分析维度
    
    def analyze_timing_characteristics(self, expr):
        """分析时序特征"""
        # 实现时序分析逻辑
        pass
    
    def analyze_power_consumption(self, expr):
        """分析功耗特征"""
        # 实现功耗分析逻辑
        pass
```

### 集成到其他工具

```python
# 集成到其他分析流程
class IntegratedAnalyzer:
    def __init__(self):
        self.linearity_analyzer = CorrectedLinearityAnalyzer()
        # 其他分析器...
    
    def comprehensive_analysis(self, dfg_file):
        # 执行综合分析
        linearity_report = self.linearity_analyzer.analyze_dfg_file(dfg_file)
        # 其他分析...
        
        return {
            'linearity': linearity_report,
            # 其他分析结果...
        }
```
