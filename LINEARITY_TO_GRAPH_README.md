# DFG线性分析结果到模拟退火算法转换器

## 概述

本模块实现了将`dfg_linearity_corrector.py`生成的DFG线性分析结果转换为`simulated_annealing.py`可以接受的图格式的完整解决方案。

## 问题背景

原始问题是需要将DFG（数据流图）线性分析的文本结果转换成NetworkX图格式，以便模拟退火算法可以对电路节点进行分区优化。

### 输入格式
- **分析结果文件**: `results/4004_dfg_linearity_analysis.txt`
- **原始DFG文件**: `dfg_files/4004_dfg.txt`

### 输出格式
- **NetworkX有向图**: 包含节点线性属性和依赖关系的图结构
- **分区结果文件**: 模拟退火优化后的节点分区方案

## 核心组件

### 1. 线性分析结果转换器 (`src/analyzers/linearity_to_graph_converter.py`)

#### 主要功能
- 解析线性分析结果文本文件
- 解析原始DFG文件获取节点依赖关系
- 创建NetworkX图结构
- 验证图的有效性

#### 核心类: `LinearityAnalysisToGraphConverter`

```python
from src.analyzers.linearity_to_graph_converter import convert_analysis_to_graph

# 简单使用方式
graph, validation = convert_analysis_to_graph("results/4004_dfg_linearity_analysis.txt")

print(f"节点数: {graph.number_of_nodes()}")
print(f"边数: {graph.number_of_edges()}")
print(f"线性节点: {validation['statistics']['linear_nodes']}")
print(f"非线性节点: {validation['statistics']['nonlinear_nodes']}")
```

#### 节点属性结构
每个节点包含以下属性：
- `is_linear`: bool - 是否为线性节点
- `reason`: str - 线性/非线性的原因
- `linearity_text`: str - "线性" 或 "非线性"
- `types`: List[str] - 信号类型（如["Wire", "Output"]）

### 2. 集成示例 (`example_workflow.py`)

完整的工作流程演示，从分析结果到优化结果：

```bash
# 基本使用
python example_workflow.py results/4004_dfg_linearity_analysis.txt

# 自定义参数
python example_workflow.py results/4004_dfg_linearity_analysis.txt \
    --iterations 1000 \
    --runs 3 \
    --temperature 150.0 \
    --verbose \
    --output-dir ./my_results
```

### 3. 模拟退火集成

#### 线性感知成本函数
```python
def linear_aware_cost_function(graph, partition):
    """考虑线性/非线性特性的成本函数"""
    cross_edge_penalty = 0
    separation_bonus = 0
    
    # 计算跨分区边的惩罚
    for src, dst in graph.edges():
        if partition.get(src, 0) != partition.get(dst, 0):
            cross_edge_penalty += 1
    
    # 计算线性/非线性分离的奖励
    # ... (详见源码)
    
    return normalized_cross_penalty - separation_bonus
```

#### 优化配置
```python
from src.simulated_annealing import SimulatedAnnealing, AnnealingConfig

config = AnnealingConfig(
    initial_temperature=100.0,
    final_temperature=0.01,
    cooling_rate=0.95,
    max_iterations=1000,
    use_adaptive_temperature=True,
    multi_start_runs=3,
    allow_nonlinear_optimization=True,
    cluster_operation_weights={
        'flip': 0.25,
        'linear_cluster': 0.35,
        'nonlinear_cluster': 0.25,
        'mixed_cluster': 0.15
    }
)

sa = SimulatedAnnealing(config)
result = sa.optimize(graph, linear_aware_cost_function)
```

## 使用流程

### 步骤1: 准备输入文件
确保有以下文件：
- DFG线性分析结果文件（如`results/4004_dfg_linearity_analysis.txt`）
- 原始DFG文件（如`dfg_files/4004_dfg.txt`）

### 步骤2: 转换为图格式
```python
from src.analyzers.linearity_to_graph_converter import convert_analysis_to_graph

graph, validation = convert_analysis_to_graph("results/4004_dfg_linearity_analysis.txt")

# 检查转换结果
if validation['is_valid']:
    print("图转换成功！")
    print(f"线性节点: {validation['statistics']['linear_nodes']}")
    print(f"非线性节点: {validation['statistics']['nonlinear_nodes']}")
```

### 步骤3: 配置和运行模拟退火
```python
from src.simulated_annealing import SimulatedAnnealing, AnnealingConfig

# 配置参数
config = AnnealingConfig(
    initial_temperature=100.0,
    max_iterations=1000,
    multi_start_runs=3
)

# 运行优化
sa = SimulatedAnnealing(config)
result = sa.optimize_multi_start(graph, cost_function)

print(f"最优成本: {result.best_cost}")
print(f"迭代次数: {result.iteration_count}")
```

### 步骤4: 分析结果
```python
# 分析分区质量
partition_stats = analyze_partition_quality(graph, result.best_partition)
print(f"跨分区边比例: {partition_stats['cross_edge_ratio']:.4f}")
print(f"分区平衡度: {partition_stats['balance_ratio']:.4f}")

# 保存结果
with open("partition_result.txt", "w") as f:
    for node, partition_id in result.best_partition.items():
        linearity = "线性" if graph.nodes[node]['is_linear'] else "非线性"
        f.write(f"{node}\t{partition_id}\t{linearity}\n")
```

## 测试

运行测试套件：
```bash
# 运行转换器测试
python -m pytest tests/test_linearity_converter.py -v

# 运行集成测试
python test_integration.py

# 运行完整工作流程测试
python example_workflow.py results/4004_dfg_linearity_analysis.txt --verbose
```

## 输出结果说明

### 图统计信息
- **总节点数**: 包括所有信号节点
- **总边数**: 信号之间的依赖关系数量
- **线性节点数**: `is_linear=True`的节点数
- **非线性节点数**: `is_linear=False`的节点数
- **未知节点数**: `is_linear=None`的节点数

### 分区结果
分区结果文件格式：
```
# 节点名称    分区号    线性属性    原因
alu.signal1    0        线性       直接终端赋值
alu.signal2    1        非线性     非线性算子:And
...
```

### 优化指标
- **跨分区边比例**: 分区间连接的边占总边数的比例（越小越好）
- **分区平衡度**: 两个分区节点数的平衡程度（0-1，越接近1越好）
- **成本改进百分比**: 相对初始解的改进程度

## 实际运行示例

使用提供的测试数据运行：
```bash
$ python example_workflow.py results/4004_dfg_linearity_analysis.txt --verbose --iterations 800 --runs 2

=== DFG线性分析结果到模拟退火优化工作流程 ===

1. 转换线性分析结果为图格式...
   ✓ 转换成功!
   - 节点数: 107
   - 边数: 198
   - 线性节点: 13
   - 非线性节点: 65
   - 未知节点: 29

2. 配置模拟退火算法...
   ✓ 配置完成
   - 初始温度: 100.0
   - 最大迭代: 800
   - 多起点运行: 2

3. 执行模拟退火优化...
   ✓ 优化完成!
   - 最优成本: 0.255793
   - 总迭代次数: 800
   - 收敛原因: 达到最大迭代次数

4. 分析优化结果...
   ✓ 分析完成!
   - 成本改进: 14.82%
   - 跨分区边比例: 0.4242
   - 分区平衡度: 0.8448

   分区分布详情:
     分区0: 总计49个节点
       - 线性: 3 (6.1%)
       - 非线性: 31 (63.3%)
       - 未知: 15 (30.6%)
     分区1: 总计58个节点
       - 线性: 10 (17.2%)
       - 非线性: 34 (58.6%)
       - 未知: 14 (24.1%)

=== 工作流程完成! ===
```

## 文件结构

```
src/analyzers/
├── linearity_to_graph_converter.py  # 核心转换器
└── dfg_linearity_corrector.py       # 原有的线性分析器

tests/
└── test_linearity_converter.py      # 转换器测试

example_workflow.py                   # 完整工作流程示例
test_integration.py                   # 集成测试
```

## 依赖项

- Python 3.8+
- NetworkX
- NumPy
- pytest (用于测试)

## 扩展和定制

### 自定义成本函数
可以根据具体需求实现不同的成本函数：

```python
def custom_cost_function(graph, partition):
    """自定义成本函数"""
    # 实现您的成本计算逻辑
    return cost_value
```

### 调整优化参数
根据电路规模和优化目标调整模拟退火参数：

```python
config = AnnealingConfig(
    initial_temperature=200.0,  # 较大的初始温度用于更广泛的搜索
    final_temperature=0.001,    # 较小的最终温度用于精细优化
    cooling_rate=0.98,          # 较慢的冷却速度
    max_iterations=2000,        # 更多迭代次数
    multi_start_runs=5          # 更多起点运行
)
```

这个解决方案提供了从DFG线性分析结果到模拟退火优化的完整转换流程，支持自定义参数和扩展功能。