# From design to hardware

[User guide](README.md) · English · [简体中文](../zh-CN/hardware.md)

[OpenSci](https://opensci-optics.com/) connects optical design to component purchasing and assembly. Use the engine to develop the optical system locally, then continue with your OpenSci Account to obtain a component list, pricing, and a hardware configuration.

## The workflow

**Design → simulate → Local Validation → component and assembly configuration → order → hardware delivery**

Choose the route that fits your experiment:

| Route | What you purchase |
| --- | --- |
| Optical components | The optics selected by the design, with an Optical Layout Drawing |
| Experimental assembly | Optics and their mechanical assembly configuration |
| Existing optical table | A configuration that uses your own table, without a new breadboard |
| Assembly service | Hardware with the available OpenSci assembly service |

## Connect your Account

Create an Agent token in your [OpenSci Account](https://account.opensci-optics.com/?lang=en) and complete the token setup shown there. Set `OPENSCI_API_URL` to the OpenSci service, then inspect the connection:

```bash
export OPENSCI_API_URL=https://opensci-optics.com
opensci-engine account status
```

In Windows PowerShell, set the variable with `$env:OPENSCI_API_URL = "https://opensci-optics.com"`.

The `protected` extra from the [installation guide](installation.md) supports opening assembly previews and details.

## Get a configuration

Use a run with a `PASS` Local Validation:

```bash
opensci-engine resolve run
```

The response contains a `resolution_id`, the Customer Purchase BOM, current prices, and the assembly configuration. Variants include:

```bash
opensci-engine resolve run --optics-only
opensci-engine resolve run --no-breadboard
opensci-engine resolve run --assembly-service
```

Inspect the chosen resolution and its preview, replacing `RESOLUTION_ID` with the returned identifier:

```bash
opensci-engine resolution show RESOLUTION_ID --locale en
opensci-engine assembly preview RESOLUTION_ID --view
```

The resolution describes how component positioning and retained degrees of freedom are implemented. Use `--locale zh-CN` for Chinese text. The assembly preview applies to configurations that include an assembly.

## Place the order

Choose the shipping address in your OpenSci Account and review the component list, total, and agreement. The following command creates the order for the selected resolution:

```bash
opensci-engine order create RESOLUTION_ID
```

Follow the payment instructions in the order. After transferring payment, report the transfer with `opensci-engine order report-transfer ORDER_ID`. OpenSci confirms receipt and makes the corresponding drawing deliverables available.

For an assembly order:

```bash
opensci-engine assembly drawing RESOLUTION_ID --out drawing --locale en
```

For an optics-only order:

```bash
opensci-engine order layout ORDER_ID --out layout --locale en
```

Use `--locale zh-CN` to produce Chinese drawings. Drawings are available as SVG and PDF.

Explore the platform and available products at **[opensci-optics.com](https://opensci-optics.com/)**.
