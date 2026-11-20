"""
Revisión de calidad del mapa fusionado (Módulo P1)
--------------------------------------------------
Lee la nube .ply generada por mapeo_manual.py y reporta métricas para juzgar
si el mapa quedó bien ANTES de anclar las cajas 3D:

  1. Conteo, extensión (bbox = tamaño aprox. del recorrido) y centroide.
  2. Densidad: distancia media al vecino más cercano vs. el voxel usado.
     (Si >> voxel => nube con huecos / sub-muestreada.)
  3. Suelo: ajusta un plano (RANSAC). Reporta % de puntos del suelo,
     su "grosor" (std punto->plano) y el ángulo de su normal contra +Z.
       - Grosor alto  => deriva del tracking / ghosting (paredes-suelos dobles).
       - Ángulo alto  => el suelo NO quedó horizontal (revisar Z_UP / deriva).
  4. Ruido: % de puntos que un filtro estadístico marca como atípicos.
  5. (Opcional) guarda una versión limpia y abre el visor 3D.

Uso:
    python revisar_mapa.py
    python revisar_mapa.py "C:\\ruta\\a\\mapa.ply" --voxel 0.02
    python revisar_mapa.py --guardar-limpio     # escribe mapa_limpio.ply
    python revisar_mapa.py --sin-visor          # solo reporte de texto
"""

import os
import sys
import argparse
import numpy as np
import open3d as o3d

DIR = os.path.join(os.path.expanduser("~"), "Proyecto_ZED_P1")
DEFECTO = os.path.join(DIR, "mapa_manual.ply")


def seccion(t):
    print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60, flush=True)


def main():
    ap = argparse.ArgumentParser(description="Reporte de calidad de la nube fusionada")
    ap.add_argument("ply", nargs="?", default=DEFECTO, help="Ruta al .ply (defecto: mapa_manual.ply)")
    ap.add_argument("--voxel", type=float, default=0.02, help="Voxel con el que se generó el mapa (m)")
    ap.add_argument("--muestra", type=int, default=80000, help="N puntos para métricas de densidad")
    ap.add_argument("--guardar-limpio", action="store_true", help="Guarda mapa_limpio.ply sin outliers")
    ap.add_argument("--sin-visor", action="store_true", help="No abrir el visor 3D al final")
    args = ap.parse_args()

    if not os.path.exists(args.ply):
        print(f"[ERROR] No existe: {args.ply}")
        sys.exit(1)

    seccion("CARGA")
    pcd = o3d.io.read_point_cloud(args.ply)
    pts = np.asarray(pcd.points)
    N = len(pts)
    if N == 0:
        print("[ERROR] La nube está vacía."); sys.exit(1)
    tiene_color = len(pcd.colors) == N
    print(f"Archivo : {args.ply}")
    print(f"Puntos  : {N:,}")
    print(f"Color   : {'sí' if tiene_color else 'NO'}")

    # --- 1. Extensión y centroide ---
    seccion("1) EXTENSIÓN (tamaño del recorrido)")
    mn, mx = pts.min(0), pts.max(0)
    size = mx - mn
    cen = pts.mean(0)
    print(f"BBox min  (x,y,z): {mn[0]:7.2f} {mn[1]:7.2f} {mn[2]:7.2f}  m")
    print(f"BBox max  (x,y,z): {mx[0]:7.2f} {mx[1]:7.2f} {mx[2]:7.2f}  m")
    print(f"Tamaño    (x,y,z): {size[0]:7.2f} {size[1]:7.2f} {size[2]:7.2f}  m")
    print(f"Centroide (x,y,z): {cen[0]:7.2f} {cen[1]:7.2f} {cen[2]:7.2f}  m")
    print(f"-> Z (altura) abarca {size[2]:.2f} m. En Z_UP, esto es piso->techo del recorrido.")

    # --- 2. Densidad ---
    seccion("2) DENSIDAD")
    m = min(args.muestra, N)
    idx = np.random.choice(N, m, replace=False)
    sub = pcd.select_by_index(idx)
    d = np.asarray(sub.compute_nearest_neighbor_distance())
    d = d[np.isfinite(d)]
    print(f"Muestra            : {m:,} puntos")
    print(f"Dist. vecino medio : {d.mean()*1000:6.1f} mm   (mediana {np.median(d)*1000:.1f} mm)")
    print(f"Voxel del mapa     : {args.voxel*1000:6.1f} mm")
    ratio = d.mean() / args.voxel
    if ratio < 1.5:
        print("-> Densidad sana (vecinos ~ al voxel). Nube bien poblada.")
    elif ratio < 3:
        print("-> Densidad media: hay algo de hueco. Aceptable para mapeo grueso.")
    else:
        print("-> Nube DISPERSA (vecinos >> voxel): muchos huecos. Considera --sub menor al mapear.")

    # --- 3. Suelo (plano dominante) ---
    seccion("3) SUELO / DERIVA")
    try:
        modelo, inliers = pcd.segment_plane(distance_threshold=max(0.02, args.voxel),
                                            ransac_n=3, num_iterations=1000)
        a, b, c, dd = modelo
        nrm = np.array([a, b, c]); nrm /= np.linalg.norm(nrm)
        # distancia punto->plano de los inliers => grosor
        pin = pts[inliers]
        dist = np.abs(pin @ nrm + dd / np.linalg.norm([a, b, c]))
        ang = np.degrees(np.arccos(min(1.0, abs(nrm[2]))))  # vs eje Z
        pct = 100 * len(inliers) / N
        print(f"Plano dominante    : {pct:5.1f}% de los puntos")
        print(f"Grosor (std p->plano): {dist.std()*1000:6.1f} mm   (máx {dist.max()*1000:.0f} mm)")
        print(f"Ángulo normal vs +Z: {ang:5.1f}°")
        if ang < 8:
            print("-> El plano dominante es ~horizontal: es el SUELO y respeta Z_UP. ✔")
        else:
            print("-> Plano NO horizontal: o el dominante es una pared, o hubo deriva/Z mal puesto.")
        if dist.std() < 0.02:
            print("-> Suelo delgado: poca deriva, vistas bien alineadas. ✔")
        elif dist.std() < 0.05:
            print("-> Grosor moderado: leve deriva acumulada (normal en recorridos largos).")
        else:
            print("-> Suelo GRUESO: deriva/ghosting notable (superficies dobladas). Revisar tracking.")
    except Exception as e:
        print(f"[WARN] No se pudo ajustar el plano: {e}")

    # --- 4. Ruido / outliers ---
    seccion("4) RUIDO (outliers estadísticos)")
    try:
        _, keep = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        fuera = N - len(keep)
        print(f"Outliers           : {fuera:,}  ({100*fuera/N:5.2f}%)")
        if fuera / N < 0.03:
            print("-> Nube limpia. ✔")
        elif fuera / N < 0.10:
            print("-> Ruido moderado: un filtro estadístico lo deja fino.")
        else:
            print("-> Mucho ruido: conviene limpiar antes de usar el mapa.")
        if args.guardar_limpio:
            limpio = pcd.select_by_index(keep)
            out = os.path.join(os.path.dirname(args.ply), "mapa_limpio.ply")
            o3d.io.write_point_cloud(out, limpio)
            print(f"[OK] Guardado limpio: {out}  ({len(keep):,} puntos)")
    except Exception as e:
        print(f"[WARN] Filtro de outliers falló: {e}")

    seccion("RESUMEN")
    print("Revisa arriba las 4 marcas: densidad, suelo horizontal, grosor del suelo (deriva) y ruido.")
    print("Si las 4 salen ✔, el mapa está listo para anclar las cajas 3D.")

    if not args.sin_visor:
        print("\n[INFO] Abriendo visor 3D (suelo en rojo, marco de ejes en el origen). 'Q' cierra.")
        try:
            vis = o3d.geometry.PointCloud(pcd)
            if 'inliers' in dir():
                col = np.asarray(vis.colors) if len(vis.colors) == N else np.tile([0.6, 0.6, 0.6], (N, 1))
                col = np.array(col); col[inliers] = [1.0, 0.2, 0.2]
                vis.colors = o3d.utility.Vector3dVector(col)
            ejes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)
            o3d.visualization.draw_geometries([vis, ejes], window_name="Revisión del mapa")
        except Exception as e:
            print(f"[WARN] Visor no disponible: {e}")


if __name__ == "__main__":
    main()
