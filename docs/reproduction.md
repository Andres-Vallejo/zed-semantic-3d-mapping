# Exploring and running the project

## View the results first

The videos and CSVs can be explored without a ZED camera. After cloning or downloading the repository, open `docs/videos.html` in a browser to play the included MP4 videos with controls.

The raw `.svo2` recordings, complete annotations and large `.ply` maps are not included. Full reconstruction, training and the video renderer need those original inputs or equivalent new data.

## Environment

The source targets Python with NumPy, OpenCV, Open3D, Ultralytics and the ZED Python API. The archived training environment records Python 3.12, Ultralytics 8.4.86, PyTorch 2.11.0+cu128 and pyzed 5.3. These identify the original environment; the complete hardware-dependent workflow has not been revalidated as part of portfolio packaging.

Create an isolated Python environment and install the Python dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

ZED processing additionally requires the matching **ZED SDK, NVIDIA driver/CUDA stack and pyzed wheel**. Install pyzed using the installer supplied with the ZED SDK rather than an unrelated package with a similar name. See the [official Python integration documentation](https://docs.stereolabs.com/docs/development/api-languages/python).

Dependency requirements from the training workspace are preserved. They are not an exact environment lock file.

## Run the hardware-independent consolidation stage

From the repository root, with NumPy installed:

```powershell
python geometry/consolidar_detecciones.py --csv results/mapping/detecciones_3d.csv --out results/mapping/consolidated-local.csv
```

The original code runs on the saved detection table without loading the camera SDK or model. With its current defaults it produces **48 groups**, compared with **29** in the archived consolidated table. The original archived arguments are not known. Group counts depend on association, filtering and floor-extension options; this command is a way to exercise the code, not an exact recreation of the archived visualization.

## Inspect a frame or generate a map

Replace `C:\data\recording.svo2` with your recording:

```powershell
python geometry/replay_svo.py "C:\data\recording.svo2" --frame 100
python geometry/mapeo_manual.py "C:\data\recording.svo2"
```

The original geometry scripts generally write to **`~/Proyecto_ZED_P1`**. They preserve that behavior. Several scripts provide output-path flags; inspect `--help` before running a stage. The mapper opens a visualization window when finished.

## Detect and consolidate objects

```powershell
python geometry/deteccion_obb.py "C:\data\recording.svo2" --modelo models/best.pt --cada 15 --mundo --guardar-jpg --csv results/mapping/detections-local.csv
python geometry/consolidar_detecciones.py --csv results/mapping/detections-local.csv --out results/mapping/consolidated-local.csv
```

Use the same recording, units, coordinate convention and origin settings as the map. World-coordinate tracking processes the recording sequentially, even when detection is performed only on sampled frames.

## Retrain with the original preparation scripts

The dataset must be provided separately. From `training/`, the original workflow is:

```powershell
cd training
python scripts/labelme_to_yolo_seg.py
python scripts/split_dataset.py --images data/images/raw_annotated --labels data/labels/raw --val-ratio 0.2
python scripts/train.py --model yolo11n-seg.pt --data configs/dataset.yaml --epochs 80 --imgsz 640 --batch 8 --name zed_real_yolo11n
```

Prepare LabelMe JSON/image pairs under `training/data/labelme/` first. The segmentation initialization checkpoint is a separate input; the command may download it if the Ultralytics runtime supports that and it is not present locally. Some original preparation scripts clear generated destination directories before writing new files, so use a dedicated dataset workspace.

The included relative dataset configuration expects `training/data/`. Set its `path` to an absolute location if your Ultralytics data-directory settings resolve it elsewhere.

The original split script randomly partitions individual images. For an independent evaluation, create partitions by recording/session and add a separate test session instead of using that random split. The source has been retained as the original project implementation.

## Render a new demonstration

`geometry/video_demo.py` combines an existing point-cloud map, consolidated objects, camera poses and annotated JPG frames. These must come from a compatible run. The complete inputs are not included, but the rendered project videos are available in `media/`.

## Source preservation

The 13 geometry scripts and 10 training scripts were copied without code edits. `source-manifest.json` records their SHA-256 hashes at packaging time. Documentation, the relative dataset configuration and portfolio media were added around those sources.
