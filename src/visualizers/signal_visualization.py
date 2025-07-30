#!/usr/bin/env python3
"""
信号连接关系图表生成器
基于分析结果生成可视化图表
"""

import json
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def load_analysis_data():
    """加载分析数据"""
    try:
        with open("4004_signal_connections.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("请先运行 signal_connection_analyzer.py 生成分析数据")
        return None

def create_signal_distribution_chart(data):
    """创建信号类型分布图"""
    categories = data['summary']['category_distribution']
    
    # 创建饼图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 饼图 - 信号类型分布
    labels = list(categories.keys())
    sizes = list(categories.values())
    colors = plt.cm.get_cmap('tab20')(np.linspace(0, 1, len(labels)))
    
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                       colors=colors, startangle=90)
    ax1.set_title('Intel 4004 ALU 信号类型分布', fontsize=14, fontweight='bold')
    
    # 柱状图 - 连接类型分布
    conn_types = data['summary']['connection_type_distribution']
    ax2.bar(conn_types.keys(), conn_types.values(), 
            color=['skyblue', 'lightcoral'])
    ax2.set_title('连接类型分布', fontsize=14, fontweight='bold')
    ax2.set_ylabel('连接数')
    
    plt.tight_layout()
    plt.savefig('4004_signal_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_fan_in_out_analysis(data):
    """创建扇入扇出分析图"""
    signals = data['signals']
    
    # 提取扇入扇出数据
    fan_ins = []
    fan_outs = []
    signal_names = []
    categories = []
    
    for name, info in signals.items():
        fan_ins.append(info['fan_in'])
        fan_outs.append(info['fan_out'])
        signal_names.append(name.split('.')[-1])  # 只保留信号名部分
        categories.append(info['category'])
    
    # 创建散点图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 扇入扇出散点图
    category_colors = {
        'general_input': 'red',
        'general_output': 'green',
        'accumulator': 'blue',
        'carry_flag': 'purple',
        'clock_input': 'orange',
        'arithmetic_wire': 'brown',
        'internal_wire': 'gray',
        'internal_register': 'cyan',
        'temporary_register': 'magenta',
        'other': 'black'
    }
    
    for i, (fin, fout, category) in enumerate(zip(fan_ins, fan_outs, categories)):
        color = category_colors.get(category, 'black')
        ax1.scatter(fin, fout, c=color, alpha=0.7, s=50, label=category)
    
    ax1.set_xlabel('扇入 (Fan-in)')
    ax1.set_ylabel('扇出 (Fan-out)')
    ax1.set_title('信号扇入扇出分布', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 去重legend
    handles, labels = ax1.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax1.legend(by_label.values(), by_label.keys(), 
               bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # 复杂度分布直方图
    complexities = [fin + fout for fin, fout in zip(fan_ins, fan_outs)]
    ax2.hist(complexities, bins=10, color='lightblue', alpha=0.7, edgecolor='black')
    ax2.set_xlabel('复杂度 (扇入+扇出)')
    ax2.set_ylabel('信号数量')
    ax2.set_title('信号复杂度分布', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('4004_fan_in_out_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_critical_path_visualization(data):
    """创建关键路径可视化"""
    critical_paths = data['summary']['critical_paths']
    if not critical_paths:
        print("未发现关键路径")
        return
    
    # 选择最长的路径进行可视化
    longest_path = critical_paths[0]
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 计算节点位置
    num_nodes = len(longest_path)
    positions = {}
    
    # 垂直布局
    for i, node in enumerate(longest_path):
        x = 1
        y = num_nodes - i
        positions[node] = (x, y)
    
    # 绘制节点
    signals = data['signals']
    for node in longest_path:
        x, y = positions[node]
        
        # 根据信号类型选择颜色
        if node in signals:
            category = signals[node]['category']
            if category == 'general_input':
                color = 'lightgreen'
            elif category == 'general_output':
                color = 'lightcoral'
            elif category == 'accumulator':
                color = 'lightblue'
            elif category == 'carry_flag':
                color = 'yellow'
            else:
                color = 'lightgray'
        else:
            color = 'white'
        
        # 绘制圆形节点
        circle = patches.Circle((x, y), 0.3, facecolor=color, 
                               edgecolor='black', linewidth=2)
        ax.add_patch(circle)
        
        # 添加标签
        node_label = node.replace('alu.', '')
        ax.text(x + 0.4, y, node_label, fontsize=10, 
                verticalalignment='center')
    
    # 绘制连接线
    for i in range(len(longest_path) - 1):
        node1 = longest_path[i]
        node2 = longest_path[i + 1]
        x1, y1 = positions[node1]
        x2, y2 = positions[node2]
        
        ax.arrow(x1, y1-0.3, 0, -0.4, head_width=0.1, 
                head_length=0.1, fc='black', ec='black')
    
    ax.set_xlim(0, 3)
    ax.set_ylim(0, num_nodes + 1)
    ax.set_aspect('equal')
    ax.set_title(f'关键路径可视化\n({longest_path[0].replace("alu.", "")} → {longest_path[-1].replace("alu.", "")})', 
                fontsize=14, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig('4004_critical_path.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_signal_hierarchy_chart(data):
    """创建信号层次结构图"""
    signals = data['signals']
    
    # 按类别分组信号
    by_category = defaultdict(list)
    for name, info in signals.items():
        by_category[info['category']].append((name, info))
    
    # 创建层次结构图
    fig, ax = plt.subplots(figsize=(14, 10))
    
    y_pos = 0
    category_positions = {}
    all_signals = []
    last_scatter = None
    
    # 为每个类别分配垂直位置
    for category, signals_in_cat in by_category.items():
        # 按复杂度排序
        signals_in_cat.sort(key=lambda x: x[1]['fan_in'] + x[1]['fan_out'], reverse=True)
        
        category_positions[category] = y_pos
        
        # 绘制类别标题
        ax.text(-0.5, y_pos, category.replace('_', ' ').title(), 
                fontsize=12, fontweight='bold', 
                verticalalignment='center')
        
        # 绘制该类别的信号
        for i, (signal_name, info) in enumerate(signals_in_cat[:8]):  # 只显示前8个
            x = i * 1.5
            complexity = info['fan_in'] + info['fan_out']
            
            # 根据复杂度设置大小和颜色
            size = max(50, complexity * 10)
            color_intensity = min(1.0, complexity / 10.0)
            
            last_scatter = ax.scatter(x, y_pos, s=size, alpha=0.7, 
                               c=color_intensity, cmap='Reds', 
                               edgecolors='black', linewidth=1)
            
            # 添加标签
            label = signal_name.replace('alu.', '')[:8]  # 截断长标签
            ax.text(x, y_pos - 0.3, label, fontsize=8, 
                   ha='center', rotation=45)
            
            all_signals.append((x, y_pos, complexity))
        
        y_pos -= 2
    
    # 添加颜色条
    if last_scatter is not None:
        cbar = plt.colorbar(last_scatter, ax=ax, shrink=0.8)
        cbar.set_label('复杂度 (扇入+扇出)', rotation=270, labelpad=15)
    
    ax.set_xlim(-1, 12)
    ax.set_ylim(y_pos, 1)
    ax.set_title('Intel 4004 ALU 信号层次结构\n(气泡大小和颜色表示复杂度)', 
                fontsize=14, fontweight='bold')
    ax.set_xlabel('信号索引 (按复杂度排序)')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('4004_signal_hierarchy.png', dpi=300, bbox_inches='tight')
    plt.close()

def generate_summary_report(data):
    """生成总结报告"""
    summary = data['summary']
    
    print("\n=== Intel 4004 ALU 信号连接关系分析总结 ===")
    print(f"总信号数: {summary['total_signals']}")
    print(f"主要信号数: {summary['primary_signals']}")
    print(f"连接数: {summary['total_connections']}")
    print(f"最大扇入: {summary['max_fan_in']}")
    print(f"最大扇出: {summary['max_fan_out']}")
    
    print(f"\n信号类型分布:")
    for category, count in sorted(summary['category_distribution'].items()):
        percentage = (count / summary['primary_signals']) * 100
        print(f"  {category:<20}: {count:3d} ({percentage:5.1f}%)")
    
    print(f"\n连接类型分布:")
    for conn_type, count in summary['connection_type_distribution'].items():
        percentage = (count / summary['total_connections']) * 100
        print(f"  {conn_type:<15}: {count:3d} ({percentage:5.1f}%)")
    
    print(f"\n关键信号: {summary['critical_signals']}")
    print(f"关键路径数量: {len(summary['critical_paths'])}")
    
    if summary['critical_paths']:
        longest = summary['critical_paths'][0]
        print(f"最长路径: {longest[0].replace('alu.', '')} → {longest[-1].replace('alu.', '')} (长度: {len(longest)})")

def main():
    """主函数"""
    print("=== Intel 4004 ALU 信号连接关系图表生成器 ===")
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 加载数据
    data = load_analysis_data()
    if data is None:
        return
    
    print("1. 生成信号类型分布图...")
    create_signal_distribution_chart(data)
    
    print("2. 生成扇入扇出分析图...")
    create_fan_in_out_analysis(data)
    
    print("3. 生成关键路径可视化...")
    create_critical_path_visualization(data)
    
    print("4. 生成信号层次结构图...")
    create_signal_hierarchy_chart(data)
    
    print("5. 生成总结报告...")
    generate_summary_report(data)
    
    print(f"\n生成的图表文件:")
    print(f"  - 4004_signal_distribution.png (信号类型分布)")
    print(f"  - 4004_fan_in_out_analysis.png (扇入扇出分析)")
    print(f"  - 4004_critical_path.png (关键路径)")
    print(f"  - 4004_signal_hierarchy.png (信号层次结构)")

if __name__ == "__main__":
    main()
