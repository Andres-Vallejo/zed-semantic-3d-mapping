"""
Sprint F — Mapeo multivista (Módulo P1)
---------------------------------------
Reconstruye la escena fusionando TODOS los frames del .svo con Spatial Mapping +
positional tracking del ZED SDK. Al fusionar vistas:
  - el ruido aleatorio de la profundidad se promedia y se cancela,
  - se rellena la geometría oculta (caras que no se ven desde un solo frame).

Este es el corazón del enfoque de MAPEO (no metrología): un mapa 3D consistente
de la escena/objeto, no una medición certificada.

REQUISITO: el .svo debe tener MOVIMIENTO de cámara (haber rodeado el objeto).
Si la grabación es de un punto fijo, no hay vistas nuevas que fusionar y el
resultado será casi igual a un solo frame -> habría que pedir a P2 una toma
rodeando el objeto.

Uso:
    python mapeo_multivista.py "C:\\ruta\\a\\tu.svo"
    python mapeo_multivista.py "...tu.svo" --tipo mesh --res 0.02

Salida: mapa_fusionado.ply (o .obj si es malla) en C:\\Users\\<tu>\\Proyecto_ZED_P1\\
"""

import os
import sys
import argparse
import pyzed.sl as sl

DIR = os.path.join(os.path.expanduser("~"), "Proyecto_ZED_P1")
os.makedirs(DIR, exist_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Mapeo multivista con Spatial Mapping")
    ap.add_argument("svo")
    ap.add_argument("--tipo", choices=["nube", "mesh"], default="nube",
                    help="nube = FusedPointCloud, mesh = malla")
    ap.add_argument("--res", type=float, default=0.05,
                    help="Resolución del mapa en metros (más chico = más detalle, más pesado)")
    ap.add_argument("--max-dist", type=float, default=3.5,
                    help="Alcance máximo del mapeo en metros")
    ap.add_argument("--max-frames", type=int, default=0,
                    help="Límite de frames a procesar (0 = todos). Útil para prueba rápida.")
    ap.add_argument("--depth", choices=["neural_light", "neural", "neural_plus"],
                    default="neural_light",
                    help="Modo de profundidad. neural_light = más rápido (recomendado para mapeo).")
    args = ap.parse_args()

    DEPTH = {
        "neural_light": sl.DEPTH_MODE.NEURAL_LIGHT,
        "neural": sl.DEPTH_MODE.NEURAL,
        "neural_plus": sl.DEPTH_MODE.NEURAL_PLUS,
    }[args.depth]

    # --- Apertura ---
    init = sl.InitParameters()
    init.set_from_svo_file(args.svo)
    init.svo_real_time_mode = False
    init.depth_mode = DEPTH
    init.coordinate_units = sl.UNIT.METER
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Z_UP
    init.depth_maximum_distance = args.max_dist

    zed = sl.Camera()
    if zed.open(init) != sl.ERROR_CODE.SUCCESS:
        print("[ERROR] No se pudo abrir el .svo")
        sys.exit(1)

    total = zed.get_svo_number_of_frames()
    print(f"[OK] SVO abierto. Frames: {total}")

    # --- Positional tracking (necesario para fusionar vistas) ---
    if zed.enable_positional_tracking(sl.PositionalTrackingParameters()) != sl.ERROR_CODE.SUCCESS:
        print("[ERROR] No se pudo activar positional tracking.")
        zed.close()
        sys.exit(1)

    # --- Spatial mapping ---
    map_params = sl.SpatialMappingParameters()
    map_params.resolution_meter = args.res
    map_params.range_meter = args.max_dist
    map_params.use_chunk_only = True
    map_params.max_memory_usage = 2048          # tope de memoria del mapa (MB)
    map_params.save_texture = False             # sin textura: menos memoria
    print(f"[DIAG] map res={args.res} m, range={args.max_dist} m, depth={args.depth}", flush=True)
    if args.tipo == "mesh":
        map_params.map_type = sl.SPATIAL_MAP_TYPE.MESH
        contenedor = sl.Mesh()
        salida = os.path.join(DIR, "mapa_fusionado.obj")
    else:
        map_params.map_type = sl.SPATIAL_MAP_TYPE.FUSED_POINT_CLOUD
        contenedor = sl.FusedPointCloud()
        salida = os.path.join(DIR, "mapa_fusionado.ply")

    est_map = zed.enable_spatial_mapping(map_params)
    print(f"[DIAG] enable_spatial_mapping -> {est_map}", flush=True)
    if est_map != sl.ERROR_CODE.SUCCESS:
        print("[ERROR] No se pudo activar spatial mapping.")
        zed.close()
        sys.exit(1)

    # --- Recorrer todos los frames; el mapeo se acumula solo ---
    rt = sl.RuntimeParameters()
    n = 0
    print(f"[INFO] Entrando al bucle (secuencial, todos los frames). "
          f"Verás cada uno de los primeros 5...", flush=True)
    try:
        while True:
            estado = zed.grab(rt)            # SECUENCIAL: no saltamos, el tracking lo exige
            if estado == sl.ERROR_CODE.SUCCESS:
                n += 1
                if n <= 5 or n % 25 == 0:    # primeros 5 + cada 25
                    pos = zed.get_svo_position()
                    print(f"   procesados {n}  (frame {pos}/{total}, "
                          f"mapeo: {zed.get_spatial_mapping_state()})", flush=True)
                if args.max_frames and n >= args.max_frames:
                    print(f"[OK] Límite de {args.max_frames} frames alcanzado.", flush=True)
                    break
            elif estado == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
                print(f"[OK] Fin del SVO. Frames procesados: {n}", flush=True)
                break
            else:
                print(f"[WARN] grab devolvió {estado}; deteniendo.", flush=True)
                break
    except Exception as e:
        import traceback
        print("[EXCEPCIÓN] en el bucle:", e, flush=True)
        traceback.print_exc()

    # --- Extraer y guardar el mapa fusionado ---
    print("[INFO] Extrayendo mapa fusionado (puede tardar)...")
    zed.extract_whole_spatial_map(contenedor)
    zed.disable_spatial_mapping()
    zed.disable_positional_tracking()
    zed.close()

    contenedor.save(salida)
    print(f"[OK] Mapa guardado en {salida}")

    # --- Visualizar con Open3D ---
    try:
        import open3d as o3d
        geom = o3d.io.read_triangle_mesh(salida) if args.tipo == "mesh" \
            else o3d.io.read_point_cloud(salida)
        if args.tipo == "mesh":
            geom.compute_vertex_normals()
        print("[INFO] Visor 3D del mapa fusionado. 'Q' para cerrar.")
        o3d.visualization.draw_geometries([geom], window_name="Mapa multivista (Sprint F)")
    except Exception as e:
        print(f"[INFO] Mapa guardado; no se pudo visualizar aquí ({e}). "
              f"Ábrelo en MeshLab o ZED.")


if __name__ == "__main__":
    main()
