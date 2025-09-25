# 文件说明（4004_dfg_bind_masks.json）

---

## 1. JSON 文件结构

顶层结构：
```json
{
  "file": "dfg_files/4004_dfg.txt",      // 源 DFG 文件路径
  "binds": [ ... ],                      // Bind 粒度的分析结果数组
  "total_binds": 123                     // 绑定总数
}
```

### 每个 bind 对象结构
```json
{
  "dest": "alu.acc",                    // 目标信号名
  "dest_location": 42,                   // 目标信号在 Verilog 文件中的行号（无则为 null）
  "ast": { ... },                        // AST 扁平化结构（见下）
  "operator_order": [0, 1, ...],         // 运算符节点顺序（AST 节点 id）
  "operator_mask": [1, 0, ...],          // 运算符可翻转掩码（1=线性）
  "workset_order": [0, 2, ...],          // 可掩码工作集节点顺序（含 operator/concat/partselect）
  "workset_mask": [1, 0, ...],           // 工作集掩码
  "workset_intrinsic_mask": [1, 1, ...], // 工作集本征线性掩码
  "fusable_adj": [[0,2],[2,5],...],      // 可融合邻接（工作集节点 id 对）
  "bind_has_branch": false,              // 是否含有分支节点
  "sources": ["alu.data", ...],         // 源信号名数组
  "source_locations": [17, 23, ...],     // 源信号在 Verilog 文件中的行号（无则为 null）
  "operator_count": 3,                   // 运算符节点数
  "bind_kind": "opchain",               // 绑定类型（alias/constant/branch/opchain）
  "maskable_count": 2,                   // 可掩码工作集节点数
  "is_trivial": false,                   // 是否为平凡绑定
  "const_value": "4'b0000",             // 若为常量绑定，常量值
  "workset_labels": ["alu.acc#op0:Plus", ...] // 工作集人类可读标签
}
```

#### AST 节点结构（ast 字段）
```json
"ast": {
  "nodes": {
    "0": { "id": 0, "type": "operator", "value": "Plus", "children": [1,2], "is_linear": true, ... },
    "1": { ... },
    ...
  },
  "root": 0
}
```

---

## 2. 字段含义详解
- **dest**：本绑定的目标信号名。
- **dest_location**：目标信号在原 Verilog 文件中的行号（找不到则为 null）。
- **sources**：本绑定依赖的源信号名数组。
- **source_locations**：每个源信号在 Verilog 文件中的行号（找不到则为 null）。
- **operator_order / workset_order**：AST 中 operator/工作集节点的遍历顺序（节点 id）。
- **operator_mask / workset_mask**：对应节点是否可翻转（线性）掩码。
- **workset_intrinsic_mask**：本征线性掩码（不依赖子树线性）。
- **fusable_adj**：可融合邻接（用于后续聚类/优化）。
- **bind_kind**：绑定类型：
  - alias：直接赋值
  - constant：常量绑定
  - branch：含有分支节点
  - opchain：一般运算链
- **is_trivial**：是否为平凡绑定（无可掩码单元）。
- **const_value**：常量绑定时的值。
- **workset_labels**：工作集节点的人类可读标签。
- **ast**：表达式树的扁平化结构，便于遍历和定位。

---

## 3. 典型调用方式

### Python 读取示例
```python
import json
with open('results/4004_dfg_bind_masks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for bind in data['binds']:
    print(bind['dest'], bind['dest_location'], bind['sources'], bind['source_locations'])
    # 可进一步处理 ast、掩码、邻接等
```

### 用于 Verilog 运算符替换的典型流程
1. 读取 JSON，筛选 `dest_location`/`source_locations` 不为 null 的绑定。
2. 跳过 DFG 临时变量（如 `_rn_`）。
3. 结合行号，定位原 Verilog 文件的目标行。
4. 按需替换表达式中的运算符（如 - → onn_minus）。

---

## 4. 注意事项
- 行号信息依赖 Verilog 解析器，若信号为 DFG 中间变量或未在原文件声明，则为 null。
- 绑定类型、掩码等信息可辅助后续聚类、优化、代码生成等自动化任务。
- 若需批量处理多个文件，建议统一接口和路径规范。

---

## 5. 相关工具与扩展
- 可结合 `esimulator/utils/verilog_parser.py` 获取信号-行号映射。
- 可用 `src/analyzers/dfg_linearity_corrector.py` 直接生成带行号的掩码 JSON。
- 支持 CLI 一键生成：
  ```sh
  python esimulator_cli.py analyze dfg_files/xxx_dfg.txt --verilog-file verilog_files/xxx.v --module-prefix alu.
  ```
