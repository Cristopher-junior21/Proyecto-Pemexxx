# Cangrejera — formulario de Eventos corregido (v1.1)

Este parche **sustituye la mejora v1.0** de Eventos. No requiere actualizar MySQL, ni modifica la lógica de Python.

## Problema corregido
En la captura, las etiquetas del formulario se superponían con las cajas de texto porque estaban colocadas en filas alternadas de una cuadrícula que se comprimía al renderizar. Agregar solo una barra de desplazamiento no eliminó ese problema.

Ahora cada etiqueta y su control están juntos dentro de un bloque vertical con altura mínima. Se distribuyen en dos columnas (en vez de tres), se separan en Datos generales, Fechas y horarios y Ubicación y estado y se conserva un desplazamiento vertical dentro de Eventos.

## Instalar en el repositorio existente
1. Cierra el sistema y guarda un commit antes de reemplazar archivos.
2. Extrae el ZIP y copia **solo** `ui/main.ui` y `ui/style.qss` a `C:\Users\crist\Proyecto-Pemexxx\ui\`.
3. En VS Code, desde `C:\Users\crist\Proyecto-Pemexxx`, ejecuta:

```powershell
.\.venv\Scripts\python.exe main.py
```

4. En Eventos, baja con la rueda del ratón. La tabla seguirá después del formulario y sus botones.

**Se conservan todos los objectName existentes**, incluidos `txtClaveEvento`, `cmbClasificacionEvento`, `btnCursoGuardar` y `tablaCursos`, así como los estilos institucionales.

## Verificaciones
- XML analizado correctamente.
- Todos los nombres de controles antiguos siguen presentes, sin duplicados.
- Pendiente: prueba visual real dentro de tu Windows con PySide6.
