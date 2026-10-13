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

## 示例中的精简摘要

在仓库根目录运行示例：

```bash
python examples/beam_expander.py --out run-example
python examples/ideal_lens_focus.py --out run-ideal-focus
```

每个示例向标准输出写入一个 JSON 摘要。结构化字段名使用英文，诊断信息写入标准错误。默认输出包含整体 `status`、`engine_status`、可为空的 `validation_status`，以及目标标识、指标、实际值、单位、适用的上下界、判定结果和可用的消息或问题代码。摘要还保留需要处理的 `issues`、`model_scope_issues` 和 `element_models`，以及 `identity` 和 `integrity` 信息。存在功率数据时，精简的 `power_budget` 仅包含标量汇总值和 `total_sinks`；添加 `--details` 可查看完整功率明细。

`artifacts` 和 `exports` 字段指向磁盘上的完整数据。扩束示例保存原生本地运行记录和到达光束 CSV，并提供打开三维场景的 `view_command`。理想透镜示例无需下载目录，会将请求、仿真结果、光线和到达光束数据保存在 `--out` 指定的目录中。其底层 API 结果不包含原生本地运行清单或三维查看器命令。两个示例的默认输出目录分别为 `run-example` 和 `run-ideal-focus`。

读取已保存的原生本地运行记录，无需重新仿真：

```bash
python examples/result_summary.py run-example
python examples/result_summary.py run-example --details
```

摘要工具先验证已保存的运行记录，再通过公开结果 API 生成摘要。此命令读取扩束示例或 `opensci-engine project run` 生成的原生本地运行产物；理想透镜示例的输出是底层 API 结果文件集。[result_summary.py](../../examples/result_summary.py) 提供可复用的 Python 函数 `summarize_results(results, *, artifacts=None, details=False)` 和 `summarize_run(directory, *, details=False)`，两者均返回可用于 JSON 输出的字典。

示例脚本和已保存运行摘要命令使用以下退出码：

| 退出码 | 报告的结果 |
| --- | --- |
| `0` | `PASS`、`WARNING` 或 `NOT_APPLICABLE` |
| `1` | `FAIL` |
| `2` | `UNKNOWN` |
| `3` | `OUT_OF_MODEL_SCOPE` |
| `4` | 输入、产物完整性、运行时或命令用法错误 |

设计结果即使未通过，也会生成 JSON 摘要并保留完整数据。退出码 `4` 会向标准错误写入 JSON 错误信息，标准输出为空。这些示例错误码与引擎 CLI 的文件和用法错误码分别定义。

理想透镜示例可通过 `--maximum-radius-mm` 修改目标上限（默认 `0.05`）。以下命令分别使用默认目标、预期不通过的更严格目标和无效输入：

```bash
python examples/ideal_lens_focus.py --out run-focus-default
python examples/ideal_lens_focus.py --out run-focus-strict --maximum-radius-mm 0.001
python examples/ideal_lens_focus.py --maximum-radius-mm -1
```

半径上限必须为有限非负数，`nan` 也属于无效输入。每条命令运行后，可立即在 PowerShell 中查看 `$LASTEXITCODE`，或在 POSIX shell 中查看 `$?`。两个示例均支持 `--details`，用于在摘要中包含完整功率明细；完整光线数据可通过已保存的产物路径访问。

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
