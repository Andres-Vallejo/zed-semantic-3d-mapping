"""
Sprint B — Recorte 2D -> 3D con máscara mock (Módulo P1)
--------------------------------------------------------
Implementa el CONTRATO DE DATOS del equipo:
    ENTRADA:  máscara 2D (o caja 2D)  +  nube de puntos del frame
    SALIDA:   nube recortada con SOLO el objeto (aislado del fondo)

Como aún no hay YOLO de P3, la máscara es "mock": la dibujas a mano con un
recuadro sobre la imagen, o pasas un .png de máscara (mismo tamaño que la imagen).
Cuando llegue la máscara real de SAM/YOLO, solo cambias la fuente con --mask.

Uso:
    # recuadro interactivo (arrastra el mouse, ENTER para confirmar)
    python recorte_mascara.py "ruta\\a\\tu.svo"

    # caja fija
    python recorte_mascara.py "ruta\\a\\tu.svo" --bbox 320 180 200 240

    # máscara real (png binario: blanco=objeto)
    python recorte_mascara.py "ruta\\a\\tu.svo" --mask mascara.png

Guarda la nube recortada en objeto_recortado.ply (entrada del Sprint C-E).
"""

import os
import sys
import argparse
import numpy as np
import cv2
import pyzed.sl as sl
import open3d as o3d

# Carpeta de salida escribible (la del proyecto en Cowork es de solo lectura para
# tu proceso). Usamos una carpeta en tu home y la creamos si no existe.
DIR = os.path.join(os.path.expanduser("~"), "Proyecto_ZED_P1")
os.makedirs(DIR, exist_ok=True)


def cargar_frame(svo_path, frame, max_dist):
    init = sl.InitParameters()
    init.set_from_svo_file(svo_path)
    init.svo_real_time_mode = False
    init.depth_mode = sl.DEPTH_MODE.NEURAL
    init.coordinate_units = sl.UNIT.METER
    # Marco de mundo con Z hacia arriba (mapeo), en vez del IMAGE por defecto
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Z_UP
    init.depth_maximum_distance = max_dist

    zed = sl.Camera()
    if zed.open(init) != sl.ERROR_CODE.SUCCESS:
        print("[ERROR] No se pudo abrir el .svo")
        sys.exit(1)

    if frame > 0:
        total = zed.get_svo_number_of_frames()
        zed.set_svo_position(min(frame, total - 1))

    image = sl.Mat()
    pcd_mat = sl.Mat()
    if zed.grab(sl.RuntimeParameters()) != sl.ERROR_CODE.SUCCESS:
        print("[ERROR] No se pudo leer el frame.")
        zed.close()
        sys.exit(1)

    zed.retrieve_image(image, sl.VIEW.LEFT)
    zed.retrieve_measure(pcd_mat, sl.MEASURE.XYZRGBA)

    rgb = image.get_data()[:, :, :3].copy()   # BGR
    pc = pcd_mat.get_data().copy()            # HxWx4 (X,Y,Z,RGBA)
    zed.close()
    return rgb, pc


def obtener_mascara(rgb, args):
    """Devuelve una máscara booleana HxW: True donde está el objeto."""
    H, W = rgb.shape[:2]

    if args.mask:  # máscara real desde archivo
        m = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)
        if m is None:
            print(f"[ERROR] No se pudo leer la máscara {args.mask}")
            sys.exit(1)
        if m.shape[:2] != (H, W):
            m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
        return m > 127

    if args.bbox:  # caja fija x y w h
        x, y, w, h = args.bbox
    else:          # recuadro interactivo
        print("[INFO] Arrastra un recuadro sobre el objeto y presiona ENTER (C para cancelar).")
        x, y, w, h = cv2.selectROI("Selecciona el objeto", rgb, showCrosshair=True)
        cv2.destroyAllWindows()
        if w == 0 or h == 0:
            print("[ERROR] No se seleccionó ninguna región.")
            sys.exit(1)

    mask = np.zeros((H, W), dtype=bool)
    mask[y:y + h, x:x + w] = True
    print(f"[OK] Caja: x={x} y={y} w={w} h={h}")
    return mask


def main():
    ap = argparse.ArgumentParser(description="Recorte 2D->3D con máscara mock")
    ap.add_argument("svo")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--max-dist", type=float, default=8.0)
    ap.add_argument("--bbox", type=int, nargs=4, metavar=("X", "Y", "W", "H"))
    ap.add_argument("--mask", help="PNG de máscara binaria (blanco=objeto)")
    ap.add_argument("--out", default=os.path.join(DIR, "objeto_recortado.ply"))
    args = ap.parse_args()

    # Si pasan ruta relativa, anclarla a la carpeta del script
    if not os.path.isabs(args.out):
        args.out = os.path.join(DIR, args.out)

    rgb, pc = cargar_frame(args.svo, args.frame, args.max_dist)
    mask = obtener_mascara(rgb, args)

    # --- Aplicar la máscara a la nube organizada ---
    xyz = pc[:, :, :3]                          # HxWx3
    colors = rgb[:, :, ::-1] / 255.0            # BGR->RGB, HxWx3

    sel = mask & np.isfinite(xyz).all(axis=2)   # objeto + puntos válidos
    obj_xyz = xyz[sel]
    obj_rgb = colors[sel]
    print(f"[OK] Puntos del objeto: {len(obj_xyz):,}")

    if len(obj_xyz) == 0:
        print("[ERROR] La región no contiene puntos 3D válidos (¿muy lejos / sin textura?).")
        sys.exit(1)

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(obj_xyz.astype(np.float64))
    cloud.colors = o3d.utility.Vector3dVector(obj_rgb.astype(np.float64))

    ok = o3d.io.write_point_cloud(args.out, cloud)
    if not ok:
        print(f"[ERROR] No se pudo escribir en {args.out} (¿carpeta sin permiso?).")
        sys.exit(1)
    print(f"[OK] Nube del objeto guardada en {args.out}")

    print("[INFO] Visor 3D: deberías ver SOLO el objeto, sin fondo. 'Q' para cerrar.")
    o3d.visualization.draw_geometries([cloud], window_name="Objeto recortado (Sprint B)")


if __name__ == "__main__":
    main()
