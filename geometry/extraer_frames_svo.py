"""
Extrae imágenes (cámara izquierda rectificada) de un archivo .svo grabado
con la ZED2, para usarlas como dataset de etiquetado 2D.

Por qué la izquierda rectificada:
    - El ZED SDK usa la cámara izquierda como referencia del sistema.
    - La inferencia del detector correrá sobre esa misma imagen, así que
      el dataset de entrenamiento debe coincidir exactamente con ella.

Uso:
    python extraer_frames_svo.py grabacion.svo --salida frames --paso 15

    --paso N : guarda 1 de cada N frames (evita imágenes casi idénticas).
               Con grabación a 30 fps, --paso 15 da ~2 imágenes por segundo.

Requisitos:
    - ZED SDK instalado
    - pyzed (API de Python del ZED SDK)
    - opencv-python   (pip install opencv-python)
"""

import argparse
import os
import sys

import cv2
import pyzed.sl as sl


def extraer(ruta_svo, dir_salida, paso):
    if not os.path.isfile(ruta_svo):
        sys.exit(f"No se encontró el archivo: {ruta_svo}")

    os.makedirs(dir_salida, exist_ok=True)

    # Abrir el .svo como fuente (en lugar de la cámara en vivo)
    init = sl.InitParameters()
    init.set_from_svo_file(ruta_svo)
    init.svo_real_time_mode = False        # procesar tan rápido como se pueda
    init.depth_mode = sl.DEPTH_MODE.NONE   # no necesitamos profundidad para extraer RGB

    zed = sl.Camera()
    estado = zed.open(init)
    if estado != sl.ERROR_CODE.SUCCESS:
        sys.exit(f"No se pudo abrir el .svo: {estado}")

    runtime = sl.RuntimeParameters()
    imagen = sl.Mat()
    total = zed.get_svo_number_of_frames()
    base = os.path.splitext(os.path.basename(ruta_svo))[0]

    print(f"Frames en el .svo: {total} | guardando 1 de cada {paso}")

    guardadas = 0
    while True:
        estado = zed.grab(runtime)
        if estado == sl.ERROR_CODE.SUCCESS:
            pos = zed.get_svo_position()
            if pos % paso == 0:
                # VIEW.LEFT = imagen izquierda RECTIFICADA
                zed.retrieve_image(imagen, sl.VIEW.LEFT)
                frame_bgra = imagen.get_data()
                # quitar el canal alfa: muchas herramientas de etiquetado
                # esperan imágenes de 3 canales (BGR/RGB)
                frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)
                ruta_out = os.path.join(dir_salida, f"{base}_{pos:06d}.png")
                cv2.imwrite(ruta_out, frame_bgr)
                guardadas += 1
        elif estado == sl.ERROR_CODE.END_OF_SVO_FILE_REACHED:
            break
        else:
            print(f"Aviso: se detuvo la lectura ({estado})")
            break

    zed.close()
    print(f"Listo: {guardadas} imágenes guardadas en '{dir_salida}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrae frames RGB (izquierda rectificada) de un .svo de la ZED2"
    )
    parser.add_argument("svo", help="ruta al archivo .svo")
    parser.add_argument("--salida", default="frames",
                        help="carpeta de salida (por defecto: frames)")
    parser.add_argument("--paso", type=int, default=15,
                        help="guarda 1 de cada N frames (por defecto: 15)")
    args = parser.parse_args()
    extraer(args.svo, args.salida, args.paso)
