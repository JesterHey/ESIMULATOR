#!/usr/bin/env python3
"""
修正前后对比分析
展示现有方法和修正方法的差异
"""

def compare_analysis_methods():
    """对比分析方法"""
    
    print("=" * 80)
    print("DFG线性分析方法对比")
    print("=" * 80)
    
    print("\n📊 【原始方法 vs 修正方法】对比")
    print("-" * 60)
    
    # 从之前的结果读取数据
    original_results = {
        'total_operations': 465,
        'linear_operations': 294,
        'nonlinear_operations': 171,
        'linearity_ratio': 0.632,
        'method': '运算符级别统计'
    }
    
    corrected_results = {
        'total_expressions': 80,
        'linear_expressions': 13,
        'nonlinear_expressions': 67,
        'linearity_ratio': 0.162,
        'method': '表达式级别分析'
    }
    
    print(f"{'指标':<20} {'原始方法':<15} {'修正方法':<15} {'说明'}")
    print("-" * 70)
    print(f"{'分析单位':<20} {'运算符':<15} {'信号表达式':<15} {'修正：按表达式分析'}")
    print(f"{'总数量':<20} {original_results['total_operations']:<15} {corrected_results['total_expressions']:<15} {'465个运算符 → 80个表达式'}")
    print(f"{'线性数量':<20} {original_results['linear_operations']:<15} {corrected_results['linear_expressions']:<15} {'294个运算符 → 13个表达式'}")
    orig_ratio = f"{original_results['linearity_ratio']:.1%}"
    corr_ratio = f"{corrected_results['linearity_ratio']:.1%}"
    print(f"{'线性比例':<20} {orig_ratio:<15} {corr_ratio:<15} {'63.2% → 16.2%'}")
    
    print(f"\n🎯 【关键差异分析】")
    print("-" * 40)
    print("1. 线性度评估差异:")
    print(f"   - 原始方法: {original_results['linearity_ratio']:.1%} 线性")
    print(f"   - 修正方法: {corrected_results['linearity_ratio']:.1%} 线性")
    print(f"   - 差异: {original_results['linearity_ratio']*100 - corrected_results['linearity_ratio']*100:.1f}个百分点")
    
    print("\n2. 分析粒度差异:")
    print("   - 原始方法: 统计每个运算符的类型")
    print("   - 修正方法: 分析整个信号表达式的性质")
    
    print("\n3. 实际意义:")
    print("   - 原始结果误导: 暗示ALU有较高线性度")
    print("   - 修正结果真实: 显示ALU主要是非线性电路")

def analyze_specific_cases():
    """分析具体案例"""
    
    print(f"\n🔍 【具体案例分析】")
    print("-" * 50)
    
    cases = [
        {
            'signal': 'alu.acb_ib',
            'expression': '~((x31_clk2 | ~xch) & (x21_clk2 | ~iow))',
            'original_count': {'Unot': 3, 'And': 1, 'Or': 2},
            'original_analysis': '3个非线性 + 3个非线性 = 6个非线性运算符',
            'corrected_analysis': '整个表达式非线性（包含逻辑运算）'
        },
        {
            'signal': 'alu._rn4_dout', 
            'expression': 'concat(n0358, n0366, n0359, n0357)',
            'original_count': {'Concat': 1},
            'original_analysis': '1个线性运算符',
            'corrected_analysis': '整个表达式线性（纯位拼接）'
        },
        {
            'signal': 'alu.n0345',
            'expression': 'kbp & (acc_out == 4\'b1000)',
            'original_count': {'And': 1, 'Eq': 1},
            'original_analysis': '2个非线性运算符',
            'corrected_analysis': '整个表达式非线性（包含比较和逻辑与）'
        }
    ]
    
    for i, case in enumerate(cases, 1):
        print(f"\n案例 {i}: {case['signal']}")
        print(f"表达式: {case['expression']}")
        print(f"原始分析: {case['original_analysis']}")
        print(f"修正分析: {case['corrected_analysis']}")
        if i == 1:
            print("  → 原始方法正确识别为非线性")
        elif i == 2:
            print("  → 两种方法都正确识别为线性")
        else:
            print("  → 原始方法正确识别为非线性")

def show_correction_principles():
    """展示修正原则"""
    
    print(f"\n📋 【修正方案核心原则】")
    print("-" * 50)
    
    principles = [
        {
            'title': '1. 表达式级别分析',
            'description': '按信号表达式分析，而非单个运算符统计',
            'example': 'a + (b & c) → 整体非线性，而不是50%线性'
        },
        {
            'title': '2. 层次结构考虑',
            'description': '理解表达式的嵌套结构和运算优先级',
            'example': '~(A & B) → 先计算&，再计算~，整体非线性'
        },
        {
            'title': '3. 表达式类型分类',
            'description': '区分终端赋值、运算符表达式、分支表达式等',
            'example': 'Branch表达式本质上是非线性的'
        },
        {
            'title': '4. 严格线性定义',
            'description': '重新审视运算符的线性分类',
            'example': '位移运算在某些情况下应视为非线性'
        },
        {
            'title': '5. 整体性判断',
            'description': '一个表达式包含任何非线性运算，整体就是非线性',
            'example': '线性运算的组合仍然线性，但与非线性运算组合就非线性'
        }
    ]
    
    for principle in principles:
        print(f"\n{principle['title']}")
        print(f"  原则: {principle['description']}")
        print(f"  示例: {principle['example']}")

def implementation_recommendations():
    """实现建议"""
    
    print(f"\n🛠️ 【实现建议】")
    print("-" * 40)
    
    recommendations = [
        "1. 废弃现有的运算符级别统计方法",
        "2. 实现表达式树递归解析器",
        "3. 为每种表达式类型设计专门的分析逻辑",
        "4. 建立严格的线性运算符白名单",
        "5. 增加表达式复杂度分级",
        "6. 提供详细的非线性原因分析",
        "7. 支持可视化表达式树结构",
        "8. 增加用户可配置的线性标准"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    print(f"\n⚠️  【重要警告】")
    print("-" * 30)
    print("原始方法的63.2%线性度结果是严重误导的！")
    print("修正后的16.2%线性度更准确地反映了ALU的实际特征。")
    print("在任何技术报告或论文中都应使用修正后的结果。")

if __name__ == "__main__":
    compare_analysis_methods()
    analyze_specific_cases()
    show_correction_principles()
    implementation_recommendations()
