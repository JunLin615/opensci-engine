"""Focus a Gaussian beam with an ideal thin lens, using the low-level API.

使用底层 API，计算高斯光束通过理想薄透镜后的聚焦。
This example runs without a catalog download. 本示例无需下载目录。
Usage / 用法: python examples/ideal_lens_focus.py
"""

import json

from opensci_engine import ValidationRequest, builders as B, validate
from opensci_engine.contracts import ProjectSnapshot, Target


def main():
    project = ProjectSnapshot(
        components=(
            B.laser("L", wavelength_nm=532.0, waist_radius_mm=1.0,
                    position=(0, 0, 20), direction=(1, 0, 0)),
            B.thin_lens("Lens", focal_length_mm=100.0, clear_radius_mm=12.7,
                        position=(10, 0, 20), axis=(1, 0, 0)),
        ),
        observations=(
            B.observation_plane("focus", position=(110, 0, 20),
                                normal=(1, 0, 0), radius_mm=5.0),
        ),
        targets=(
            Target(target_id="spot_radius", metric="beam_radius_mm",
                   observation_id="focus", maximum=0.05),
        ),
    )
    result = validate(ValidationRequest(project=project))
    print(json.dumps({
        "status": result.status.value,
        "beam_radius_mm": result.targets[0].value,
        "target_maximum_mm": 0.05,
    }, indent=2))


if __name__ == "__main__":
    main()
