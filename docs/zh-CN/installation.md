# 安装

[用户指南](README.md) · [English](../en/installation.md) · 简体中文

OpenSci Engine 支持 Windows、macOS 和 Linux，要求 **Python 3.11 及以上版本**。编写 Python 脚本或使用 Notebook 时选择 pip；只需要独立命令行工具时可选择 uv。

## 让示例与安装版本一致

已验证的 PyPI 基线是 **0.8.0**，记录在
[engine-baseline.json](../../engine-baseline.json)。复现该版本时，使用
[0.8.0 快照](https://github.com/JunLin615/opensci-engine/tree/2e34e1dcd3eb74c4bfbf89dccfb9393673d0ffdb)
并运行 `python -m pip install "opensci-engine[protected]==0.8.0"`。
本次修订的工作流程工具需要即将发布的 0.9.0，其全新安装验证尚待完成。
下面的最新版安装命令获取当前已发布版本，可能与准备中的工作流程要求不同；运行示例前请用
`opensci-engine doctor` 确认。

0.9.0 发布后，应在全新环境中安装该精确版本并执行对齐检查。本地候选版本运行成功不会推进已验证基线。

## Python 环境

创建虚拟环境：

```bash
python -m venv .venv
```

macOS 或 Linux 激活方式：

```bash
source .venv/bin/activate
```

Windows PowerShell 激活方式：

```powershell
.venv\Scripts\Activate.ps1
```

安装并检查引擎：

```bash
python -m pip install "opensci-engine[protected]"
opensci-engine doctor
```

命令行也可以通过 `python -m opensci_engine` 调用。如果 PowerShell 无法激活环境，可直接运行 `.venv\Scripts\python.exe -m pip install "opensci-engine[protected]"` 和 `.venv\Scripts\python.exe -m opensci_engine doctor`。

`protected` 扩展支持在硬件流程中打开装配预览和装配详情。只进行光学设计与仿真时，安装 `python -m pip install opensci-engine` 即可。

## 使用 uv 安装独立命令行工具

安装 [uv](https://docs.astral.sh/uv/) 后运行：

```bash
uv tool install "opensci-engine[protected]"
opensci-engine doctor
```

如果终端找不到命令，运行 `uv tool update-shell`，然后重新打开终端。也可以临时运行一条命令：

```bash
uvx --from "opensci-engine[protected]" opensci-engine doctor
```

## 准备光学目录

```bash
opensci-engine catalog sync
opensci-engine catalog status
```

目录会下载到本地存储中，后续仿真可以使用已保存的版本，也支持离线运行。`doctor` 检查本地安装是否就绪；`catalog sync` 从 OpenSci 获取当前目录。

## 升级

使用 pip 安装时：

```bash
python -m pip install --upgrade "opensci-engine[protected]"
```

使用 uv 工具安装时：

```bash
uv tool upgrade opensci-engine
```

运行 `opensci-engine doctor` 查看已安装版本。需要复现保留的 0.8.0 示例快照时，安装 `"opensci-engine[protected]==0.8.0"`。

[engine-baseline.json](../../engine-baseline.json)记录已验证的版本和测试环境。维护者可以通过[版本对齐流程](../engine-alignment.md)检查其他已发布版本；候选版本检查通过后也不会自动修改基线。

## 常见安装问题

| 现象 | 处理方式 |
| --- | --- |
| 安装提示 Python 版本不符 | 检查 `python --version`，使用 Python 3.11+ 或 uv 安装方式 |
| 找不到 `opensci-engine` 命令 | 激活虚拟环境，或使用 `python -m opensci_engine` |
| doctor 显示 `DOWNLOAD_ON_FIRST_USE` | 运行 `opensci-engine catalog sync`，或开始使用目录创建设计 |
| 目录下载失败 | 用 `opensci-engine catalog check` 检查连接；离线导入方式见[目录指南](catalog.md) |
| 服务要求更新引擎 | 升级软件包、更新项目目录版本，重新运行设计后再提交 |

下一步：[运行第一个光学设计](getting-started.md)。
