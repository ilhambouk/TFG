from functions import *
import gurobipy as gp
from gurobipy import GRB
import sys
import os

SOLUTION_FOLDER = "solutions"
os.makedirs(SOLUTION_FOLDER, exist_ok=True)

def main(file_path):
    hojas_dict = cargar_datos_excel(file_path)
    slots_df = procesar_slots(hojas_dict["slots"])
    comprobar_columnas_requeridas(hojas_dict)
    # Crear el modelo de optimización
    model = gp.Model("Asignacion_Horarios_Examenes")

    # Crear variables de decisión
    # x[(grado, asignatura, slot)] = 1 si la asignatura del grado se asigna al slot
    x = {}
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if "ID_asignatura" in df.columns:
            for asignatura_idx, row in df.iterrows():
                asignatura_id = row["ID_asignatura"]
                cuatrimestre_asignatura = row["Cuatrimestre"] 
                for slot_idx, slot_row in slots_df.iterrows():
                    # Verificar que el cuatrimestre del slot coincida con el de la asignatura
                    if slot_row["cuatrimestre"] == cuatrimestre_asignatura:
                        x[(grado_idx, asignatura_id, slot_row["ID_slot"])] = model.addVar(
                            vtype=GRB.BINARY,
                            name=f"x_{grado_idx}_{asignatura_id}_{slot_row['ID_slot']}")

    # Restricción 1: Preasignaciones        
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if "Fecha" in df.columns and "Hora" in df.columns:
            for _, row in df.iterrows():
                asignatura_id = row["ID_asignatura"]

                # Validar y obtener la fecha asignada
                fecha_asignada = validar_fecha(row["Fecha"])
                if fecha_asignada:
                    for slot in slots_df.itertuples():
                        if slot.datetime.date() != fecha_asignada:
                            if (grado_idx, asignatura_id, slot.ID_slot) in x:  # Validar si existe
                                model.addConstr(
                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                    name=f"Restriccion_FechaPreasignada_{asignatura_id}_{slot.ID_slot}")

                # Validar y obtener la hora asignada
                hora_asignada = validar_hora(row["Hora"])
                if hora_asignada:
                    for slot in slots_df.itertuples():
                        if slot.datetime.time() != hora_asignada:
                            if (grado_idx, asignatura_id, slot.ID_slot) in x:  # Validar si existe
                                model.addConstr(
                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                    name=f"Restriccion_HoraPreasignada_{asignatura_id}_{slot.ID_slot}")

    # Restricción 2: Cada asignatura debe asignarse a un único slot
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if "ID_asignatura" in df.columns:
            for asignatura_id in df["ID_asignatura"]:
                # La suma de las variables para esta asignatura en todos los slots debe ser igual a 1
                model.addConstr(
                    gp.quicksum(
                        x[(grado_idx, asignatura_id, slot_idx)]
                        for slot_idx in slots_df["ID_slot"]
                        if (grado_idx, asignatura_id, slot_idx) in x) == 1,
                    name=f"Restriccion_UnicoSlot_{grado_idx}_{asignatura_id}")

    # Restricción 3: Las asignaturas del mismo curso y mismo grado no pueden ser asignadas al mismo slot
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):    
        if nombre_hoja != "slots":  
            for curso in df["Curso"].unique():
                        asignaturas_curso = df[df["Curso"] == curso]["ID_asignatura"]
                        for asignatura_1 in asignaturas_curso:
                            for asignatura_2 in asignaturas_curso:
                                if asignatura_1 != asignatura_2:
                                    for slot_idx in slots_df["ID_slot"]:
                                        if (grado_idx, asignatura_1, slot_idx) in x and (grado_idx, asignatura_2, slot_idx) in x:
                                            model.addConstr(
                                                x[(grado_idx, asignatura_1, slot_idx)] +
                                                x[(grado_idx, asignatura_2, slot_idx)] <= 1,
                                                f"Restriccion_MismoCurso_{grado_idx}_{curso}_{slot_idx}")

    # Restricción 4: Al menos 29 horas de diferencia entre exámenes del mismo curso y grado
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if nombre_hoja != "slots":
            for curso in df["Curso"].unique():  # Iterar por cada curso
                asignaturas_curso = df[df["Curso"] == curso]
                for cuatrimestre in asignaturas_curso["Cuatrimestre"].unique():
                    asignaturas_cuatrimestre = asignaturas_curso[asignaturas_curso["Cuatrimestre"] == cuatrimestre]
                    asignatura_ids = asignaturas_cuatrimestre["ID_asignatura"].tolist()

                    # Comparar combinaciones de asignaturas del mismo curso
                    for i, asignatura_1 in enumerate(asignatura_ids):
                        for j, asignatura_2 in enumerate(asignatura_ids):
                            if i >= j:  # Evitar repeticiones y comparación consigo misma
                                continue
                            for slot_1 in slots_df.itertuples():
                                for slot_2 in slots_df.itertuples():
                                    if slot_1.ID_slot != slot_2.ID_slot:
                                        delta = abs((slot_1.datetime - slot_2.datetime).total_seconds()) / 3600
                                        if delta < 29:  # Menos de 29 horas de diferencia
                                            
                                            if (grado_idx, asignatura_1, slot_1.ID_slot) in x and (grado_idx, asignatura_2, slot_2.ID_slot) in x:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_1, slot_1.ID_slot)] +
                                                    x[(grado_idx, asignatura_2, slot_2.ID_slot)] <= 1,
                                                    name=f"Restriccion_29H_{grado_idx}_{asignatura_1}_{asignatura_2}_{slot_1.ID_slot}_{slot_2.ID_slot}")

    # Restricción 5: Al menos 24 horas de diferencia entre exámenes de cursos consecutivos de un grado
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if nombre_hoja != "slots":
            cursos = sorted(df["Curso"].unique())  # Ordenar los cursos
            for idx, curso_actual in enumerate(cursos):
                if idx < len(cursos) - 1:  # Verificar que existe un curso consecutivo
                    curso_siguiente = cursos[idx + 1]

                    # Filtrar asignaturas de ambos cursos
                    asignaturas_actual = df[df["Curso"] == curso_actual]
                    asignaturas_siguiente = df[df["Curso"] == curso_siguiente]

                    # Identificar cuatrimestres comunes
                    cuatrimestres_comunes = set(asignaturas_actual["Cuatrimestre"].unique()) & set(asignaturas_siguiente["Cuatrimestre"].unique())

                    for cuatrimestre in cuatrimestres_comunes:
                        # Filtrar asignaturas por cuatrimestre
                        asignaturas_cuatrimestre_actual = asignaturas_actual[asignaturas_actual["Cuatrimestre"] == cuatrimestre]
                        asignaturas_cuatrimestre_siguiente = asignaturas_siguiente[asignaturas_siguiente["Cuatrimestre"] == cuatrimestre]

                        # Obtener IDs de asignaturas
                        ids_actual = asignaturas_cuatrimestre_actual["ID_asignatura"].tolist()
                        ids_siguiente = asignaturas_cuatrimestre_siguiente["ID_asignatura"].tolist()

                        # Comparar combinaciones entre los dos cursos
                        for asignatura_1 in ids_actual:
                            for asignatura_2 in ids_siguiente:
                                for slot_1 in slots_df.itertuples():
                                    for slot_2 in slots_df.itertuples():
                                        # Calcular diferencia de tiempo
                                        delta = abs((slot_1.datetime - slot_2.datetime).total_seconds()) / 3600
                                        if delta < 24:  # Menos de 24 horas de diferencia
                                            # Añadir la restricción
                                            if (grado_idx, asignatura_1, slot_1.ID_slot) in x and (grado_idx, asignatura_2, slot_2.ID_slot) in x:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_1, slot_1.ID_slot)] +
                                                    x[(grado_idx, asignatura_2, slot_2.ID_slot)] <= 1,
                                                    name=f"Restriccion_24H_CursosConsecutivos_{grado_idx}_{asignatura_1}_{asignatura_2}_{slot_1.ID_slot}_{slot_2.ID_slot}")

    # Restricción 6: Exámenes con el mismo id deben estar en el mismo slot
    for asignatura_id in set().union(*[df["ID_asignatura"] for _, df in hojas_dict.items() if "ID_asignatura" in df.columns]):
        for slot_idx in slots_df["ID_slot"]:
            # Recoger todas las variables de decisión asociadas al mismo ID_asignatura en todos los grados
            variables_asignatura = [
                x[(grado_idx, asignatura_id, slot_idx)]
                for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items())
                if "ID_asignatura" in df.columns and asignatura_id in df["ID_asignatura"].values
                and (grado_idx, asignatura_id, slot_idx) in x
            ]
            # Forzar que todas estas variables sean iguales (si están definidas)
            if len(variables_asignatura) > 1:
                model.addConstr(
                    gp.quicksum(variables_asignatura) == len(variables_asignatura) * variables_asignatura[0],
                    name=f"Restriccion_MismoSlot_{asignatura_id}_{slot_idx}")

    # Restricción 7: fechas y horarios con restricciones en las hojas del Excel
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items()):
        if nombre_hoja != "slots": 
            for _, row in df.iterrows():
                asignatura_id = row["ID_asignatura"]
                            
                # Procesar restricciones de fecha
                if isinstance(row["Fecha"], str) and any(op in row["Fecha"] for op in [">", "<", "=", "!"]):
                    # Dividir múltiples restricciones separadas por comas
                    condiciones = [cond.strip() for cond in row["Fecha"].split(",")]
                    for condicion in condiciones:
                        operador = ''.join(filter(lambda c: c in "><=!", condicion))  # Extraer el operador
                        referencia = condicion.replace(operador, "").strip()  # Extraer la referencia

                        # Caso 1: Referencia a otra celda ('A4')
                        if referencia.startswith("A"):
                            row_index_ref = int(referencia[1:]) - 2
                            if row_index_ref < len(df):  # Validar rango
                                asignatura_ref = df.at[row_index_ref, "ID_asignatura"]
                                for slot_1 in slots_df.itertuples():
                                    for slot_2 in slots_df.itertuples():
                                        # Solo considerar slots válidos
                                        if (grado_idx, asignatura_id, slot_1.ID_slot) in x and (grado_idx, asignatura_ref, slot_2.ID_slot) in x:
                                            if operador == ">":
                                                if slot_1.ID_slot <= slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_Mayor_{asignatura_id}_{asignatura_ref}")
                                            elif operador == "<":
                                                if slot_1.ID_slot >= slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_Menor_{asignatura_id}_{asignatura_ref}")
                                            elif operador == ">=":
                                                if slot_1.ID_slot < slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_MayorIgual_{asignatura_id}_{asignatura_ref}")
                                            elif operador == "<=":
                                                if slot_1.ID_slot > slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_MenorIgual_{asignatura_id}_{asignatura_ref}")
                                            elif operador == "=":
                                                if slot_1.ID_slot != slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_Igual_{asignatura_id}_{asignatura_ref}")
                                            elif operador == "!=":
                                                if slot_1.ID_slot == slot_2.ID_slot:
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Fecha_Diferente_{asignatura_id}_{asignatura_ref}")
                        # Caso 2: Fecha explícita ('2021/05/22')
                        else:
                            fecha_referencia = validar_fecha(referencia)
                            if pd.notna(fecha_referencia):  # Validar que es una fecha válida
                                for slot in slots_df.itertuples():
                                    if (grado_idx, asignatura_id, slot.ID_slot) in x:
                                        if operador == ">":
                                            if slot.datetime <= fecha_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Fecha_Mayor_{asignatura_id}")
                                        elif operador == "<":
                                            if slot.datetime >= fecha_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Fecha_Menor_{asignatura_id}")
                                        elif operador == ">=":
                                            if slot.datetime < fecha_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Fecha_MayorIgual_{asignatura_id}")
                                        elif operador == "<=":
                                            if slot.datetime > fecha_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Fecha_MenorIgual_{asignatura_id}")
                                        elif operador == "!=":
                                            if slot_1.ID_slot == fecha_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Fecha_Diferente_{asignatura_id}")          

                # Procesar restricciones de hora
                if isinstance(row["Hora"], str) and any(op in row["Hora"] for op in [">", "<", "=", "!"]):
                    condiciones_hora = [cond.strip() for cond in row["Hora"].split(",")]
                    for condicion in condiciones_hora:
                        operador_hora = ''.join(filter(lambda c: c in "><=!", condicion))  # Extraer el operador
                        referencia_hora = condicion.replace(operador_hora, "").strip()  # Extraer la referencia
                        # Caso 1: Referencia a otra celda ('A4')
                        if referencia_hora.startswith("A"):
                            row_index_hora = int(referencia_hora[1:]) - 2
                            if row_index_hora < len(df):
                                asignatura_ref_hora = df.at[row_index_hora, "ID_asignatura"]
                                # Iterar sobre slots
                                for slot_1 in slots_df.itertuples():
                                    for slot_2 in slots_df.itertuples():
                                        # Solo considerar slots válidos
                                        if (grado_idx, asignatura_id, slot_1.ID_slot) in x and (grado_idx, asignatura_ref_hora, slot_2.ID_slot) in x:
                                            if operador_hora == ">":
                                                if slot_1.datetime.time() <= slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_Mayor_{asignatura_id}_{asignatura_ref_hora}")
                                            elif operador_hora == "<":
                                                if slot_1.datetime.time() >= slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_Menor_{asignatura_id}_{asignatura_ref_hora}")
                                            elif operador_hora == ">=":
                                                if slot_1.datetime.time() < slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_MayorIgual_{asignatura_id}_{asignatura_ref_hora}")
                                            elif operador_hora == "<=":
                                                if slot_1.datetime.time() > slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_MenorIgual_{asignatura_id}_{asignatura_ref_hora}")
                                            elif operador_hora == "=":
                                                if slot_1.datetime.time() != slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_Igual_{asignatura_id}_{asignatura_ref_hora}")
                                            elif operador_hora == "!=":
                                                if slot_1.datetime.time() == slot_2.datetime.time():
                                                    model.addConstr(
                                                        x[(grado_idx, asignatura_id, slot_1.ID_slot)] +
                                                        x[(grado_idx, asignatura_ref_hora, slot_2.ID_slot)] <= 1,
                                                        name=f"Restriccion_Hora_Diferente_{asignatura_id}_{asignatura_ref_hora}")
                        # Caso 2: Hora explícita ('10:00:00')
                        else:
                            hora_referencia = pd.to_datetime(referencia_hora, format="%H:%M", errors="raise").time()
                            if hora_referencia:  # Validar que es una hora válida
                                for slot in slots_df.itertuples():
                                    if (grado_idx, asignatura_id, slot.ID_slot) in x:
                                        if operador_hora == ">":
                                            if slot.datetime.time() <= hora_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Hora_Mayor_{asignatura_id}")
                                        elif operador_hora == "<":
                                            if slot.datetime.time() >= hora_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Hora_Menor_{asignatura_id}")
                                        elif operador_hora == ">=":
                                            if slot.datetime.time() < hora_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Hora_MayorIgual_{asignatura_id}")
                                        elif operador_hora == "<=":
                                            if slot.datetime.time() > hora_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Hora_MenorIgual_{asignatura_id}")
                                        elif operador_hora == "!=":
                                            if slot.datetime.time() == hora_referencia:
                                                model.addConstr(
                                                    x[(grado_idx, asignatura_id, slot.ID_slot)] == 0,
                                                    name=f"Restriccion_Hora_Diferente_{asignatura_id}")
                                                    
    # Función objetivo: Maximizar el tiempo entre exámenes ponderado por su dificultad
    objective = gp.quicksum(
    (
        (slots_df.loc[slot_2.ID_slot, "datetime"] - slots_df.loc[slot_1.ID_slot, "datetime"]).total_seconds() / 3600  
        if slot_2.ID_slot > slot_1.ID_slot else 0  
    )
    * asignatura_1.Peso  # Peso de la asignatura
    for grado_idx, (nombre_hoja, df) in enumerate(hojas_dict.items())
    if nombre_hoja != "slots"
    for curso in df["Curso"].unique()  # Iteramos por curso
    for cuatrimestre in df["Cuatrimestre"].unique()  # Iteramos por cuatrimestre
    for asignatura_1 in df[(df["Curso"] == curso) & (df["Cuatrimestre"] == cuatrimestre)].itertuples()
    for asignatura_2 in df[(df["Curso"] == curso) & (df["Cuatrimestre"] == cuatrimestre)].itertuples()
    if asignatura_1.ID_asignatura != asignatura_2.ID_asignatura  # Evitamos comparaciones consigo misma
    for slot_1 in slots_df.itertuples()
    for slot_2 in slots_df.itertuples()
    if slot_1.ID_slot < slot_2.ID_slot
    )

    # Establecer la función objetivo
    model.setObjective(objective, GRB.MAXIMIZE)

    # Permite buscar soluciones diversas
    model.setParam(GRB.Param.PoolSearchMode, 2)  
    model.setParam(GRB.Param.PoolSolutions, 3) # Número máximo de soluciones a almacenar 
    model.setParam(GRB.Param.PoolGap, 0.01)  # Ajusta el gap para permitir más diversidad
    model.setParam(GRB.Param.MIPFocus, 1)    # Cambia el enfoque de la búsqueda

    model.optimize()

    # Verificar si se encontraron soluciones
    if model.status == GRB.OPTIMAL:
        num_solutions = model.SolCount
        print(f"Número de soluciones encontradas: {num_solutions}")

        # Iterar sobre las soluciones encontradas
        for i in range(num_solutions):
            model.setParam(GRB.Param.SolutionNumber, i)

            # Crear un ExcelWriter para guardar la solución actual
            output_file = os.path.join(SOLUTION_FOLDER, f"solucion_{i+1}.xlsx")
            with pd.ExcelWriter(output_file) as writer:

                for grado_idx, (nombre_hoja, df_grado) in enumerate(hojas_dict.items()):
                    if "ID_asignatura" in df_grado.columns:
                        # Crear un DataFrame para almacenar las asignaciones de este grado
                        asignaciones_grado = []
                        # Extraer las asignaciones de este grado en la solución actual
                        for asignatura_idx, row in df_grado.iterrows():
                            asignatura_id = row["ID_asignatura"]
                            for slot_idx, slot_row in slots_df.iterrows():
                                if slot_row["cuatrimestre"] == "1-2":
                                    if x[(grado_idx, asignatura_id, slot_row["ID_slot"])].Xn > 0.5:
                                        # Agregar la asignación a la lista
                                        asignaciones_grado.append({
                                            "Asignatura": asignatura_id,
                                            "Curso": row["Curso"],
                                            "Cuatrimestre": row["Cuatrimestre"],
                                            "Fecha": slot_row["datetime"].date(),  # Solo la fecha
                                            "Hora": slot_row["datetime"].time(),   # Solo la hora
                                        })

                        # Crear un DataFrame con las asignaciones
                        df_solucion = pd.DataFrame(asignaciones_grado)
                        df_solucion.to_excel(writer, sheet_name=nombre_hoja, index=False)

            print(f"Solución {i+1} guardada en {output_file}")

    else:
        model.computeIIS()  # Realiza el análisis de infeasibilidad
        model.write("infeasible_model.ilp")  # Guarda el modelo infeasible en un archivo
        print("No se encontró una solución óptima.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]  # Obtén el argumento de línea de comandos
        main(file_path)
    else:
        print("Se requiere la ruta del archivo Excel como argumento.")


     