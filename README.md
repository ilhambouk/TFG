# Optimización de asignación de horarios de exámenes
Este proyecto busca automatizar y optimizar la asignación de horarios de exámenes finales. Utiliza técnicas de **Programación Lineal Entera Mixta (MILP)** y el solver **Gurobi**, implementado en **Python**, para generar horarios eficientes que minimicen la superposición de exámenes y maximicen los tiempos de preparación.  

Además, cuenta con una **interfaz web intuitiva** que facilita la configuración y exportación de los horarios generados. El sistema ha sido validado con distintos grados y escenarios complejos, garantizando soluciones óptimas en tiempos de ejecución reducidos.  

---

### 📌 Instalación y configuración  

Este proyecto tiene **dependencias externas** con el solver **Gurobi**, por lo que es necesario instalarlo y configurarlo correctamente antes de ejecutar el código.  

#### 1️⃣ Requisitos previos  
- **Python 3.8 o superior**  
- **Gurobi Optimizer** (requiere licencia académica o comercial)  

#### 2️⃣ Instalación de Gurobi  

##### 📥 Descargar e instalar Gurobi  
1. Ir a [Gurobi Website](https://www.gurobi.com/downloads/) y descargar la versión correspondiente a tu sistema operativo.  
2. Seguir las instrucciones de instalación proporcionadas en la documentación oficial.  

##### 🔑 Configurar la licencia de Gurobi  
- Si eres estudiante o perteneces a una institución académica, puedes obtener una licencia gratuita en [Gurobi Academic License](https://www.gurobi.com/academia/academic-program-and-licenses/).  
- Una vez obtenida la licencia, ejecuta el siguiente comando para activarla:  
  ```sh
  grbgetkey TU_CLAVE_DE_LICENCIA
