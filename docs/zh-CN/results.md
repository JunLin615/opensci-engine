# 结果、可视化与导出

[用户指南](README.md) · [English](../en/results.md) · 简体中文

每次运行都会生成完整的设计与仿真记录。结果 API 直接读取该记录，查看或导出数据时无需重新仿真。

## 阅读运行目录

| 文件 | 内容 |
| --- | --- |
| `manifest.json` | 整体状态、目标结果、标识和文件哈希 |
| `project.json` | 本次运行的光学项目 |
| `engine_request.json` | 传入物理引擎的输入 |
| `simulation_result.json` | 目标数值、光束、观测结果、路径、功率收支和问题记录 |
| `ray_data.json` | 主光线与瞳面采样光线的追迹数据，包括表面交点和光程 |
| `local_validation.json` | 本地验证记录，关联项目、目录、引擎和结果标识 |
| `optical_scene.json` | 结构化光学场景 |
| `optical_scene.glb` | glTF 二进制格式的三维场景 |

```bash
opensci-engine results describe run
opensci-engine results monitor run output
opensci-engine project verify run
```

`output` 是扩束示例中的观测平面标识。自己的项目可以通过 `results describe` 查看可用观测平面。

## 理解状态

| 状态 | 含义 | 后续操作 |
| --- | --- | --- |
| `PASS` | 已评估目标满足要求 | 检查数值，继续设计流程 |
| `WARNING` | 结果附有问题记录 | 阅读问题列表及相关上下文 |
| `FAIL` | 某项要求或验证检查未通过 | 查看失败目标或问题，调整项目 |
| `UNKNOWN` | 已有信息不足以确定结果 | 补充输入，或查看该指标所需条件 |
| `OUT_OF_MODEL_SCOPE` | 请求的计算超出所选模型适用范围 | 查看相关模型与参数信息 |
| `NOT_APPLICABLE` | 某项检查不适用于当前配置 | 继续查看适用的检查项 |

编写脚本时，设计命令退出码 `0` 对应 PASS/WARNING/NOT_APPLICABLE，`1` 对应 FAIL，`2` 对应 UNKNOWN，`3` 对应 OUT_OF_MODEL_SCOPE。文件和命令用法错误使用其他退出码，详见命令行参考。

## 查看与分享

```bash
opensci-engine view run
opensci-engine view run --write-html view.html
opensci-engine view run --snapshot shots
```

浏览器查看器提供预设视角、元件选择、光束显隐和中英文标签。截图输出包含正交视图 PNG、`scene_summary.json` 和图例。

## 导出表格

```bash
opensci-engine export arrivals run --format csv --out arrivals.csv
opensci-engine export rays run --format jsonl --out rays.jsonl
opensci-engine results columns arrivals
opensci-engine results metrics --name waist_distance_x_mm
```

可导出的内容包括观测面、到达光束、光线、路径、路径分段、功率收支、叠加结果、波前、辐照度和指标定义。使用 `export --help` 查看格式与筛选参数。波前导出采用追迹光程差，辐照度图采用近轴高斯光束叠加模型。

Python 调用方式：

```python
from pathlib import Path
from opensci_engine.results import load_run

results = load_run("run")
print(results.describe())
print(results.power_budget())
Path("arrivals.csv").write_bytes(results.export("arrivals", "csv"))
```

## 单位与约定

API 使用毫米表示长度、纳米表示真空波长、角度制表示角度、瓦特表示功率。高斯光束尺寸 `w` 表示**光强降至 1/e² 处的半径**。坐标系为右手系，元件局部 `+z` 为光轴。导出列名和指标说明会标明相应单位。

下一步：[从设计到硬件](hardware.md)。
