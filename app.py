from flask import Flask, request, jsonify, render_template, send_file, url_for
import os
import process_excel  # Importa el archivo de procesamiento

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
SOLUTIONS_FOLDER = "solutions"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SOLUTIONS_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ruta para la página principal
@app.route("/")
def index():
    return render_template("index.html")

# Ruta para subir el archivo
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    file = request.files["file"]
    convocatoria = request.form.get("convocatoria")  # Obtener la convocatoria del formulario
    if file.filename == "":
        return jsonify({"error": "El archivo no tiene nombre"}), 400
    if file and file.filename.endswith((".xls", ".xlsx")):
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        try:
            # si hay alguna solucion previa, eliminarla
            for archivo in os.listdir(SOLUTIONS_FOLDER):
                os.remove(os.path.join(SOLUTIONS_FOLDER, archivo))

            # Procesar el archivo Excel
            process_excel.main(file_path, convocatoria)

            os.remove(file_path)  # Eliminar el archivo de subida

            # Obtener todos los archivos generados en solutions/
            archivos_generados = os.listdir(SOLUTIONS_FOLDER)
            if not archivos_generados:
                return jsonify({"error": "Error en el procesamiento del archivo. No se generó el resultado."}), 500
            # Generar URLs de descarga para cada archivo generado
            download_urls = [
                {"filename": archivo, "url": url_for("download_file", filename=archivo, _external=True)}
                for archivo in archivos_generados
            ]
            return jsonify({"message": "Archivo procesado correctamente.", "downloads": download_urls}), 200
        except Exception as e:
            return jsonify({f"Error interno en el servidor: {str(e)}"}), 500
    else:
        return jsonify({"Formato de archivo no permitido"}), 400
    
@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(SOLUTIONS_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == "__main__":
    app.run(debug=True)
