import pandas as pd

COLUMNAS_REQUERIDAS_GRADO = {"ID_asignatura", "Curso", "Cuatrimestre", "Peso"}
COLUMNAS_REQUERIDAS_SLOT = {"Fecha", "Cuatrimestre"}

def cargar_datos_excel(file_path):
    hojas_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
    if "slots" not in hojas_dict:
        raise ValueError("El archivo Excel debe incluir una hoja llamada 'slots'.")
    return hojas_dict

def procesar_slots(slots_raw):
    slots_df = []
    for _, row in slots_raw.iterrows():
        fecha = pd.to_datetime(row["Fecha"], format="%Y-%m-%d", errors="coerce")
        if pd.isna(fecha):
            raise ValueError(f"Fecha inválida: {row['Fecha']}")
        cuatrimestre = row["Cuatrimestre"]
        for hora_col in ["Hora 1", "Hora 2"]:
            hora = row[hora_col]
            if pd.isna(hora):
                print(f"Hora vacia en columna {hora_col}: {hora}")
                continue
            # Asegurarse de que la hora se interprete correctamente
            try:
                hora_formateada = pd.to_datetime(hora, format="%H:%M:%S", errors="coerce").time()
            except ValueError:
                raise ValueError(f"Formato de hora no reconocido: {hora}")
            
            # Concatenar fecha y hora
            datetime_combined = pd.to_datetime(f"{fecha.strftime('%Y-%m-%d')} {hora_formateada.strftime('%H:%M')}", format="%Y-%m-%d %H:%M", errors="coerce")
            slots_df.append({"ID_slot": len(slots_df), "datetime": datetime_combined, "cuatrimestre": cuatrimestre})
    return pd.DataFrame(slots_df)

def validar_fecha(fecha):
    """Valida y convierte una fecha a formato datetime.date."""
    try:
        fecha_valida = pd.to_datetime(fecha, format="%Y-%m-%d", errors="raise").date()
        if pd.isna(fecha_valida):
            return None  # Retorna None si la hora es inválida o NaT
        return fecha_valida
    except ValueError:
        return None  # Retorna None si no es válida

def validar_hora(hora):
    """Valida y convierte una hora a formato datetime.time."""
    try:
        hora_valida = pd.to_datetime(hora, format="%H:%M:%S", errors="raise")
        if pd.isna(hora_valida):
            return None  # Retorna None si la hora es inválida o NaT
        return hora_valida.time()
    except ValueError:
        return None  # Retorna None si no es válida

def comprobar_columnas_requeridas(hojas_dict):
    """Comprueba si las columnas requeridas están presentes en el DataFrame."""
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if nombre_hoja != "slots":
            if not COLUMNAS_REQUERIDAS_GRADO.issubset(df.columns):
                return False
        else:
            if not COLUMNAS_REQUERIDAS_SLOT.issubset(df.columns):
                return False

