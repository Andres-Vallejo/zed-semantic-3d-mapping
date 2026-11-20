# Trained model

This directory contains the existing model exported from the project's second training run:

- `best.pt`: Ultralytics/PyTorch checkpoint.
- `best.onnx`: ONNX export.
- `classes.txt`: the original ordered class list.

The task is instance segmentation with nine classes and a training image size of 640 pixels. The source artifacts are preserved; numerical equivalence between runtimes was not established as part of this repository's packaging.

The original validation split shares recording sessions with training. See the root README for the recorded metrics and their scope.
