"""已迁移: 可视化模块

该模块已迁移到 `esimulator.visual.partition_viz`。
此文件仅做兼容性转发，后续将移除，请更新引用到新包路径。
"""

from esimulator.visual.partition_viz import (
    export_partition_dot,
    export_comparison_dot,
)

__all__ = [
    'export_partition_dot',
    'export_comparison_dot',
]
