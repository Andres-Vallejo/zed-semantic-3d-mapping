from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    images = sorted(Path("data/labelme").glob("*.jpg"))[:24]
    if not images:
        raise RuntimeError("No hay imagenes en data/labelme")
    size = (240, 135)
    thumbs = []
    for path in images:
        image = cv2.imread(str(path))
        if image is None:
            continue
        image = cv2.resize(image, size)
        cv2.putText(
            image,
            path.stem[-12:],
            (5, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        thumbs.append(image)
    cols = 4
    rows = math.ceil(len(thumbs) / cols)
    canvas = np.zeros((rows * size[1], cols * size[0], 3), dtype=np.uint8)
    for idx, image in enumerate(thumbs):
        y = (idx // cols) * size[1]
        x = (idx % cols) * size[0]
        canvas[y : y + size[1], x : x + size[0]] = image
    Path("reports").mkdir(exist_ok=True)
    out = Path("reports/contact_sheet.jpg")
    cv2.imwrite(str(out), canvas)
    print(out)


if __name__ == "__main__":
    main()
