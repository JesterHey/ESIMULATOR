# ESIMULATOR AMS 仿真脚手架

本目录提供基于 Verilog-AMS/SystemVerilog RNM 的快速联调环境，目标是将 SA 结果中的线性 bind 片段映射到“ONN 线性块（行为/实值模型）”，并用理想 ADC/DAC 完成数模接口，优先支持 Xcelium/VCS，提供纯 RNM 版本（不依赖电气学科库）与可选电气模板。

## 分阶段实施
- Phase 1: RNM 快速集成
  - 使用 `real`/`wreal` 端口建模理想 ADC/DAC 与线性块，便于快速仿真与波形观察。
  - 根据 `results/4004_bindmask_sa_best.json` 自动生成 `ams/build/` 下的每个 bind 包装与顶层汇接清单。
- Phase 2: 电气模板对接（可选）
  - 提供 `electrical` 端口的 `ideal_adc_elec`/`ideal_dac_elec` 模板，后续可替换为更真实的器件模型。
- Phase 3: 混合精度/版图考虑（后续）

## 目录结构
- `models/`：RNM 模型与电气模板
  - `ideal_adc.sv`：理想 ADC（实值 → 数字）
  - `ideal_dac.sv`：理想 DAC（数字 → 实值）
  - `onn_linear_block.sv`：ONN 线性块 RNM 占位（权重/规模可配置）
  - `ideal_adc_elec.va`/`ideal_dac_elec.va`：电气模板（可选）
- `build/`：由生成器产出的包装模块与顶层连接文件
- `tb/`：测试平台与示例顶层
  - `tb_top.sv`：4004 示例仿真顶层（占位）

## 运行步骤（示例）
1) 生成 AMS 包装

```bash
python3 tools/generate_ams_from_sa.py \
  --sa results/4004_bindmask_sa_best.json \
  --out ams/build \
  --top ams/tb/tb_top.sv
```

2) 使用仿真器（以 Xcelium 为例，需本机有 license）

```bash
# RNM（SystemVerilog）编译/仿真示例
xrun -64bit -sv \
  ams/models/ideal_adc.sv \
  ams/models/ideal_dac.sv \
  ams/models/onn_linear_block.sv \
  ams/build/*.sv \
  ams/tb/tb_top.sv
```

> 若使用 VCS，可改为：
```bash
vcs -full64 -sverilog \
  ams/models/ideal_adc.sv \
  ams/models/ideal_dac.sv \
  ams/models/onn_linear_block.sv \
  ams/build/*.sv \
  ams/tb/tb_top.sv -debug_access+all -l sim.log
./simv
```

3) 可选：电气模板（需要 Verilog-AMS 支持）
- 将 `ideal_adc_elec.va` 与 `ideal_dac_elec.va` 加入工程，并对接 `electrical` 端口版本的顶层。

## 参数建议
- `onn_linear_block`：`PARAM_INPUTS/PARAM_OUTPUTS/PARAM_WIDTH` 控制输入输出数与内部位宽；可扩展为 tile/bit slice 等参数。
- `ideal_adc/dac`：`VFS` 全幅值、`BITS` 量化位宽。

## 注意
- 当前 `tb_top.sv` 为占位，生成器会输出 `bind_*.sv` 包装与 `ams_top_bind_connect.sv` 汇接文件；你可在 `tb_top.sv` 中实例化该汇接顶层或直接作为仿真入口。
