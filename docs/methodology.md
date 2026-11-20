# Methodology

## Capture and input data

The input is a stereo-camera recording from a Stereolabs ZED 2. Offline playback provides aligned image/depth observations and permits sequential camera tracking. A moving camera observes the laboratory from multiple viewpoints.

`geometry/replay_svo.py` inspects a recorded frame. `geometry/extraer_frames_svo.py` and `training/scripts/extract_frames_zed.py` provide frame-extraction workflows used during development.

## Recognition

The team prepared a nine-class dataset and trained a YOLO11 segmentation network. LabelMe annotations are converted to YOLO segmentation labels, split into training and validation partitions, and used in the training workflow. Model exports include PyTorch and ONNX artifacts.

The class order is preserved in `models/classes.txt` and `training/configs/classes.txt`. The model predicts boxes, class scores and masks. In the original end-to-end geometry script, the predicted **bounding box** selects the corresponding region of the organized point cloud. External binary masks can be used with `geometry/recorte_mascara.py`.

## Scene reconstruction

Two reconstruction paths are present:

- `mapeo_multivista.py` uses ZED Spatial Mapping.
- `mapeo_manual.py` transforms each accepted frame's points into world coordinates using camera poses, accumulates them, and periodically applies voxel downsampling. This alternative was developed when Spatial Mapping was unstable on a project machine.

The manual mapper also exports camera poses. Coordinate units are metres, with a right-handed Z-up system. The floor-origin option must agree between mapping and detection. Using the same recording and origin settings is necessary for alignment; independent tracking runs can still introduce differences.

## From 2D detections to oriented 3D boxes

`deteccion_obb.py` selects the depth points within each accepted 2D detection. It removes non-finite and distant points, then applies voxel downsampling and statistical filtering. Plane fitting and DBSCAN clustering reduce background and isolate a candidate object cloud. An oriented bounding box is estimated, using an orientation derived from a fitted plane when available.

The exported row includes frame, class, confidence, centre, dimensions, yaw, point count and coordinate frame. These values describe the observed cloud and the geometric assumptions used by the algorithm. Partial visibility and incorrect plane selection can affect the estimate.

## Multiview consolidation

`consolidar_detecciones.py` groups observations of the same class by nearby XY centres. Per-group medians and dimension percentiles summarize the repeated observations. A minimum-view rule marks weak groups as `dudoso` and repeated groups as `ok`. Optional height filters and floor-extension assumptions are available.

This is a heuristic association and statistical consolidation stage. It does not implement a ground-truth instance tracker or fuse a complete per-object surface model. Its thresholds depend on the scene.

## Visual outputs

The project exports point-cloud maps, annotated frames, CSV tables and rendered views. `vista_lado.py` creates projected views and `video_demo.py` combines detection images with the reconstructed map and camera trajectory. The portfolio videos are compressed copies of those existing outputs, with the original duration preserved.

## Interpreting the saved results

Training and validation include nearby frames from the same recordings. The saved metrics characterize this experiment rather than performance on an independent scene. Different checkpoint epochs can optimize different metrics; the root README consistently reports the last saved epoch.

The mapping CSVs are one archived output set. Running consolidation with its current defaults produces a different number of groups because the exact arguments of the saved consolidation are not recorded. No completed dimensional-reference measurements accompany this example.

## Tools and reference

- [Stereolabs ZED SDK](https://www.stereolabs.com/en/developers): stereo depth and camera tracking.
- [Ultralytics](https://docs.ultralytics.com/tasks/segment/): instance segmentation and model training.
- [Open3D](https://www.open3d.org/): point-cloud processing and geometric representations.
- NumPy and OpenCV: numerical processing, frame preparation and visualization.
- Lahoud and Ghanem, *2D-Driven 3D Object Detection in RGB-D Images*, ICCV 2017: a conceptual reference for using 2D recognition to guide 3D localization. The project is an engineering pipeline inspired by this idea, not a claimed reproduction of the paper.
