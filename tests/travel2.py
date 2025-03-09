import os
import time

def clear_console():
    """Limpia la consola según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_frame(width, height, plane, plane_x, plane_y, clouds):
    """
    Genera un frame de la animación.
    
    Parámetros:
      - width, height: dimensiones del "canvas".
      - plane: lista de strings con el dibujo ASCII del avión.
      - plane_x, plane_y: posición superior izquierda donde dibujar el avión.
      - clouds: lista de tuplas (x, y, texto) con nubes.
    """
    # Crear una "pantalla" en blanco
    grid = [[" " for _ in range(width)] for _ in range(height)]
    
    # Dibujar la pista (runway) en la última línea
    runway_row = height - 1
    for x in range(width):
        grid[runway_row][x] = "="  # Pista representada con "="
    
    # Dibujar las nubes en posiciones fijas
    for cx, cy, cloud_text in clouds:
        if 0 <= cy < height:
            for i, char in enumerate(cloud_text):
                if 0 <= cx + i < width:
                    grid[cy][cx + i] = char
    
    # Dibujar el avión (considerando que puede tener varias líneas)
    for i, line in enumerate(plane):
        row = plane_y + i
        if 0 <= row < height:
            for j, char in enumerate(line):
                col = plane_x + j
                if 0 <= col < width:
                    grid[row][col] = char

    # Convertir la "pantalla" en una cadena
    frame_lines = ["".join(row) for row in grid]
    return "\n".join(frame_lines)

def airplane_animation():
    width = 80   # Ancho del canvas
    height = 20  # Alto del canvas

    # Definir algunas nubes (posición x, posición y y su dibujo en ASCII)
    clouds = [
        (5, 2, " (  ) "),
        (30, 4, "  (    )  "),
        (50, 3, " (o) "),
        (65, 1, " (~~~) ")
    ]
    
    # Dibujo del avión en ASCII (dos líneas)
    plane_art = [
        "   __|__",
        " ---o--(_)--o---"
    ]
    
    total_frames = 50          # Total de frames de la animación
    runway_takeoff_frame = 15  # Frame a partir del cual el avión empieza a ascender
    
    for i in range(total_frames):
        # Calcular la posición horizontal del avión
        plane_x = i * 2  # Avanza 2 espacios por frame
        if plane_x > width - len(plane_art[0]):
            plane_x = width - len(plane_art[0])
        
        # Calcular la posición vertical: en los primeros frames, el avión se sitúa cerca de la pista;
        # luego, tras el despegue, asciende gradualmente.
        if i < runway_takeoff_frame:
            plane_y = height - 3  # Justo encima de la pista
        else:
            # Cada dos frames se sube una línea
            plane_y = height - 3 - ((i - runway_takeoff_frame) // 2)
            if plane_y < 0:
                plane_y = 0
        
        # Generar el frame completo
        frame = generate_frame(width, height, plane_art, plane_x, plane_y, clouds)
        clear_console()
        print(frame)
        time.sleep(0.2)  # Pausa entre frames

    print("El avión ha despegado y volado.")

if __name__ == "__main__":
    airplane_animation()
