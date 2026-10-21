# 从设计到硬件

[用户指南](README.md) · [English](../en/hardware.md) · 简体中文

[OpenSci](https://opensci-optics.com/) 将光学设计与元件采购、装配连接起来。先使用引擎在本地完成光学系统设计，再通过 OpenSci Account 获取元件清单、价格与硬件配置。

## 工作流程

**设计 → 仿真 → 本地验证 → 元件与装配配置 → 订单 → 硬件交付**

根据实验需要选择购买方式：

| 方式 | 购买内容 |
| --- | --- |
| 光学元件 | 设计选定的光学元件，并提供光学布局图 |
| 实验装配 | 光学元件及其机械装配配置 |
| 使用已有光学平台 | 采用自己的光学平台，不购买新的面包板 |
| 装配服务 | 硬件及可选的 OpenSci 装配服务 |

## 连接 Account

从 [OpenSci 官网](https://opensci-optics.com/) 进入。Account 提供服务地址与 Agent Token 配置方式。将 `OPENSCI_API_URL` 设置为 Account 显示的地址，按页面完成 Token 配置，然后检查连接：

```bash
opensci-engine account status
```

[安装指南](installation.md)中的 `protected` 扩展支持打开装配预览和装配详情。

## 获取配置方案

使用本地验证状态为 `PASS` 的运行结果：

```bash
opensci-engine resolve run
```

返回结果包含 `resolution_id`、客户购买 BOM、当前价格和装配配置。也可以选择：

```bash
opensci-engine resolve run --optics-only
opensci-engine resolve run --no-breadboard
opensci-engine resolve run --assembly-service
```

将 `RESOLUTION_ID` 替换为返回的标识，查看选定的方案及预览：

```bash
opensci-engine resolution show RESOLUTION_ID --locale zh-CN
opensci-engine assembly preview RESOLUTION_ID --view
```

方案会说明元件定位和保留自由度的实现方式。使用 `--locale en` 可以查看英文内容。装配预览适用于包含装配的配置。

## 创建订单

在 OpenSci Account 中选择收货地址，核对元件清单、总价和协议。以下命令会为选定方案创建订单：

```bash
opensci-engine order create RESOLUTION_ID
```

按订单说明完成付款后，使用 `opensci-engine order report-transfer ORDER_ID` 报告已转账。OpenSci 确认到账后，提供相应图纸交付物。

装配订单生成详细装配图：

```bash
opensci-engine assembly drawing RESOLUTION_ID --out drawing --locale zh-CN
```

仅购买光学元件的订单生成光学布局图：

```bash
opensci-engine order layout ORDER_ID --out layout --locale zh-CN
```

使用 `--locale en` 生成英文图纸。图纸提供 SVG 和 PDF 格式。

完整产品与服务请访问 **[opensci-optics.com](https://opensci-optics.com/)**。
