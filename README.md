# Sistema de Capacitación de Cangrejera — estructura organizada v0.2

Proyecto de escritorio Python + PySide6 (Qt Designer) + MySQL 8.0.

## Dónde revisar la lógica

| Archivo | Qué contiene |
| --- | --- |
| `main.py` | Arranque del programa, sin lógica de negocio. |
| `logica/sistema.py` | Carga de Qt Designer, tablas, botones y eventos de la ventana. |
| `logica/trabajadores.py` | Registro, edición, búsqueda y desactivación de trabajadores. |
| `logica/cursos.py` | Registro, actualización, búsqueda y cancelación de cursos. |
| `logica/inscripciones.py` | Inscripciones, reinscripción y bajas de cursos. |
| `database/conexion.py` | Configuración MySQL y funciones `fetchall()`, `execute()`. |
| `database/verificar_conexion.py` | Diagnóstico de conexión independiente de la interfaz. |
| `ui/main.ui` | Ventanas, campos, tablas y botones: editable con Qt Designer. |
| `ui/style.qss` | Diseño visual y colores. |

Los nombres de los botones están enlazados en `logica/sistema.py` dentro de
`_configurar_eventos`. Para seguir una operación: ubica el botón allí, revisa
el método que llama en el módulo correspondiente y la consulta SQL.

**Importante:** no cambies el `objectName` de los widgets en Qt Designer sin
actualizar las referencias de la lógica, o el programa no encontrará el control.

## Instalación (PowerShell)

Abre esta **carpeta principal** (donde está `main.py`) en Visual Studio Code.
No ejecutes los comandos desde `ui/` o `logica/`.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

**Si ya tienes un `.env`, consérvalo y no ejecutes la copia** (para no sobreescribir tu configuración).
En `.env` coloca los datos correctos de tu MySQL local; **no subas ese archivo a GitHub**.
Este paquete no contiene ninguna contraseña real.

```ini
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=COLOCA_AQUI_TU_CONTRASENA_LOCAL
DB_NAME=sistema_capacitacion_cangrejera
```

Para revisar la conexión primero:

```powershell
.\.venv\Scripts\python.exe -m database.verificar_conexion
```

Para abrir la aplicación:

```powershell
.\.venv\Scripts\python.exe main.py
```

Para abrir Qt Designer:

```powershell
.\.venv\Scripts\pyside6-designer.exe
```

Abre `ui/main.ui` en Qt Designer para editar las pantallas.

## Diferencias respecto de v0.1

- Código dividido por módulo, ya no concentrado en `main.py`.
- `db.py` ahora es `database/conexion.py`.
- Se agregó `database/verificar_conexion.py` para comprobar MySQL antes de abrir la UI.
- La interfaz `.ui` y sus `objectName` siguen iguales.
- Se conservaron las consultas originales, sin cambiar las tablas de MySQL.

**Si actualizas la carpeta del prototipo anterior:** guarda tu archivo `.env`
y cualquier cambio propio antes de sustituir los archivos. Puedes extraer
esta versión en una carpeta nueva para revisarla y después copiarla a tu
repositorio. No necesitas volver a importar el SQL.

## Funciones pendientes

Las pantallas de cédulas y reportes aún no están programadas, y todavía
faltan la autenticación y los permisos. El paquete es un **prototipo para
pruebas con registros ficticios**, no una solución para datos reales ni uso
en producción.
