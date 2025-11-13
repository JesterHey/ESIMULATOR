#!/bin/bash
# run_complete_analysis.sh
# 使用更新后的分析逻辑重新分析 counter 和 scratchpad 模块

# --- 配置 ---
VERILOG_SOURCE_DIR="4004_full_verilog"
DFG_DIR="dfg_files"
RESULTS_DIR="results"

# --- 脚本执行 ---
echo "========================================================"
echo "开始执行完整分析流程（使用更新后的逻辑，过滤 Partselect）"
echo "========================================================"

# 确保目录存在
mkdir -p "$DFG_DIR"
mkdir -p "$RESULTS_DIR"

# --- 处理 counter 模块 ---
MODULE_NAME="counter"
echo ""
echo "----------------------------------------------------"
echo "正在处理模块: $MODULE_NAME"
echo "----------------------------------------------------"

# 检查 DFG 文件是否存在
if [ ! -f "$DFG_DIR/${MODULE_NAME}_dfg.txt" ]; then
    echo "警告: 找不到 $DFG_DIR/${MODULE_NAME}_dfg.txt"
    echo "正在生成 DFG 文件..."
    python3 esimulator/core/dfg_parser.py "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" > "$DFG_DIR/${MODULE_NAME}_dfg.txt"
    if [ $? -ne 0 ]; then
        echo "错误: 生成 $MODULE_NAME 的 DFG 文件失败。"
    else
        echo "✓ DFG 文件已生成"
    fi
else
    echo "✓ 找到现有 DFG 文件: $DFG_DIR/${MODULE_NAME}_dfg.txt"
fi

# 执行线性分析
echo "正在执行线性分析..."
OUTPUT_SUBDIR="$RESULTS_DIR/${MODULE_NAME}_result"
mkdir -p "$OUTPUT_SUBDIR"
python3 esimulator_cli.py analyze "$DFG_DIR/${MODULE_NAME}_dfg.txt" \
    --verilog-file "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" \
    --output "$OUTPUT_SUBDIR" \
    --format json \
    --module-prefix "${MODULE_NAME}."

if [ $? -ne 0 ]; then
    echo "✗ 错误: 模块 '$MODULE_NAME' 的线性分析失败。"
else
    echo "✓ 线性分析完成，结果保存在: $OUTPUT_SUBDIR"
fi

# --- 处理 instruction_pointer 模块 ---
MODULE_NAME="instruction_pointer"
echo ""
echo "----------------------------------------------------"
echo "正在处理模块: $MODULE_NAME"
echo "----------------------------------------------------"

# 检查 DFG 文件是否存在
if [ ! -f "$DFG_DIR/${MODULE_NAME}_dfg.txt" ]; then
    echo "警告: 找不到 $DFG_DIR/${MODULE_NAME}_dfg.txt"
    echo "正在生成 DFG 文件（包含 counter 依赖）..."
    python3 esimulator/core/dfg_parser.py "$VERILOG_SOURCE_DIR/counter.v" "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" > "$DFG_DIR/${MODULE_NAME}_dfg.txt"
    if [ $? -ne 0 ]; then
        echo "错误: 生成 $MODULE_NAME 的 DFG 文件失败。"
    else
        echo "✓ DFG 文件已生成"
    fi
else
    echo "✓ 找到现有 DFG 文件: $DFG_DIR/${MODULE_NAME}_dfg.txt"
fi

# 执行线性分析
echo "正在执行线性分析..."
OUTPUT_SUBDIR="$RESULTS_DIR/${MODULE_NAME}_result"
mkdir -p "$OUTPUT_SUBDIR"
python3 esimulator_cli.py analyze "$DFG_DIR/${MODULE_NAME}_dfg.txt" \
    --verilog-file "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" \
    --output "$OUTPUT_SUBDIR" \
    --format json \
    --module-prefix "${MODULE_NAME}."

if [ $? -ne 0 ]; then
    echo "✗ 错误: 模块 '$MODULE_NAME' 的线性分析失败。"
else
    echo "✓ 线性分析完成，结果保存在: $OUTPUT_SUBDIR"
fi

# --- 处理 scratchpad 模块 ---
MODULE_NAME="scratchpad"
echo ""
echo "----------------------------------------------------"
echo "正在处理模块: $MODULE_NAME"
echo "----------------------------------------------------"

# 检查 DFG 文件是否存在
if [ ! -f "$DFG_DIR/${MODULE_NAME}_dfg.txt" ]; then
    echo "警告: 找不到 $DFG_DIR/${MODULE_NAME}_dfg.txt"
    echo "正在生成 DFG 文件（包含 counter 依赖）..."
    python3 esimulator/core/dfg_parser.py "$VERILOG_SOURCE_DIR/counter.v" "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" > "$DFG_DIR/${MODULE_NAME}_dfg.txt"
    if [ $? -ne 0 ]; then
        echo "错误: 生成 $MODULE_NAME 的 DFG 文件失败。"
    else
        echo "✓ DFG 文件已生成"
    fi
else
    echo "✓ 找到现有 DFG 文件: $DFG_DIR/${MODULE_NAME}_dfg.txt"
fi

# 执行线性分析
echo "正在执行线性分析..."
OUTPUT_SUBDIR="$RESULTS_DIR/${MODULE_NAME}_result"
mkdir -p "$OUTPUT_SUBDIR"
python3 esimulator_cli.py analyze "$DFG_DIR/${MODULE_NAME}_dfg.txt" \
    --verilog-file "$VERILOG_SOURCE_DIR/$MODULE_NAME.v" \
    --output "$OUTPUT_SUBDIR" \
    --format json \
    --module-prefix "${MODULE_NAME}."

if [ $? -ne 0 ]; then
    echo "✗ 错误: 模块 '$MODULE_NAME' 的线性分析失败。"
else
    echo "✓ 线性分析完成，结果保存在: $OUTPUT_SUBDIR"
fi

# --- 统一转换为 guide.txt ---
echo ""
echo "----------------------------------------------------"
echo "正在执行 JSON 到 guide.txt 的转换..."
echo "----------------------------------------------------"
python3 json_to_guide.py

if [ $? -ne 0 ]; then
    echo "✗ 错误: JSON 到 guide.txt 的转换失败。"
else
    echo "✓ JSON 到 guide.txt 的转换完成。"
fi

# --- 显示结果 ---
echo ""
echo "========================================================"
echo "全流程处理完毕！"
echo "========================================================"
echo ""
echo "生成的文件位置："
echo "  Counter 模块："
echo "    - DFG:   $DFG_DIR/counter_dfg.txt"
echo "    - JSON:  $RESULTS_DIR/counter_result/counter_dfg_bind_masks.json"
echo "    - GUIDE: $RESULTS_DIR/counter_result/guide.txt"
echo ""
echo "  Instruction Pointer 模块："
echo "    - DFG:   $DFG_DIR/instruction_pointer_dfg.txt"
echo "    - JSON:  $RESULTS_DIR/instruction_pointer_result/instruction_pointer_dfg_bind_masks.json"
echo "    - GUIDE: $RESULTS_DIR/instruction_pointer_result/guide.txt"
echo ""
echo "  Scratchpad 模块："
echo "    - DFG:   $DFG_DIR/scratchpad_dfg.txt"
echo "    - JSON:  $RESULTS_DIR/scratchpad_result/scratchpad_dfg_bind_masks.json"
echo "    - GUIDE: $RESULTS_DIR/scratchpad_result/guide.txt"
echo ""
echo "提示: guide.txt 中已过滤掉 Partselect 操作"
echo "========================================================"
