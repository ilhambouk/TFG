import pandas as pd
import subprocess
import sys
import time
import psutil

def medir_ejecucion(script_name, file_path):
    try:
        tiempo_inicio = time.time()

        proceso = subprocess.Popen([sys.executable, script_name, file_path], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)

        # Esperar un poco para asegurarnos de que el proceso inició
        time.sleep(0.5)

        memoria_usada = 0.0  # Inicializar memoria usada
        
        if proceso.poll() is None:  # Verificar si el proceso sigue en ejecución
            proceso_psutil = psutil.Process(proceso.pid)
            memoria_usada = proceso_psutil.memory_info().rss / (1024 * 1024)  # Convertir a MB

        # Capturar salida y errores
        salida, errores = proceso.communicate()

        tiempo_fin = time.time()

        print(f"Salida de {script_name}:")
        print(salida)

        if errores:
            print("Errores encontrados:")
            print(errores)

        print(f"Tiempo de ejecución: {(tiempo_fin - tiempo_inicio) / 60:.4f} minutos")
        print(f"Memoria usada: {memoria_usada:.2f} MB")

    except Exception as e:
        print(f"Error durante el proceso: {str(e)}")

def main(file_path, convocatoria):
    if convocatoria == "ordinaria":
        medir_ejecucion("ordinaria.py", file_path)
    elif convocatoria == "extraordinaria":
        medir_ejecucion("extraordinaria.py", file_path)
    else:
        print("Convocatoria no válida. Usa 'ordinaria' o 'extraordinaria'.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        file_path = sys.argv[1]
        convocatoria = sys.argv[2]
        main(file_path, convocatoria)
    else:
        print("Se requiere la ruta del archivo Excel como argumento.")

