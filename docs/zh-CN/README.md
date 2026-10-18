# 用户指南

[首页](../../README.zh-CN.md) · [English](../en/README.md) · 简体中文

从一个可运行的光学设计开始，逐步了解结果，并将它调整为自己的实验方案。

1. [安装 OpenSci Engine](installation.md)：Python、虚拟环境、uv 和版本升级。
2. [运行第一个设计](getting-started.md)：生成项目、运行仿真、打开三维视图。
3. [使用光学目录](catalog.md)：查找元件、管理版本、复现项目。
4. [读取与导出结果](results.md)：验证状态、光束数据、可视化和 CSV 导出。
5. [继续完成硬件实现](hardware.md)：元件选型、装配预览和订购。
6. [分析测量数据](measurements.md)：背景扣除、参考归一化、线性拟合及残差图。
7. [联用外部科学工具](interop.md)：用 SciPy、Optuna、SALib、LightPipes、prysm、POPPY、Perceval、Piquasso 和 grcwa 完成优化、衍射、量子光子学和超表面元件计算。

## 示例

| 示例 | 在仓库根目录运行 | 是否使用光学目录 |
| --- | --- | --- |
| [扩束系统](../../examples/beam_expander.py) | `python examples/beam_expander.py --out run-example` | 是；首次使用时下载 |
| [理想透镜聚焦](../../examples/ideal_lens_focus.py) | `python examples/ideal_lens_focus.py` | 否；使用数学模型元件 |
| [测量数据分析](../../examples/analyze_measurements.py) | 按[两个 CSV 示例](measurements.md)运行 | 否；无需引擎，安装 `requirements-examples.txt` |
| [外部工具联用](../../examples/interop/) | 按[外部工具指南](interop.md)运行 | 否；安装各专题的依赖文件 |

运行脚本前，将软件包安装到当前 Python 环境。`uv tool install` 提供独立命令行工具；需要在 Python 中导入时，请采用 [pip 安装方式](installation.md)。

指南对应 **opensci-engine 0.8.0**。命令参数可通过 `--help` 查看；Python API 说明可查阅已安装的软件包和 [PyPI 参考文档](https://pypi.org/project/opensci-engine/)。

[OpenSci 官网](https://opensci-optics.com/) · [软件包版本](https://pypi.org/project/opensci-engine/#history) · [交流与反馈](https://github.com/JunLin615/opensci-engine/issues/new/choose)
