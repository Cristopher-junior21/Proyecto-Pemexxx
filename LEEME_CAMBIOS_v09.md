# Cangrejera — Actualización unificada v0.9

Paquete preparado para **copiar su contenido** dentro del repositorio existente: `C:\Users\crist\Proyecto-Pemexxx`.
No abras este ZIP como proyecto nuevo; no copies un directorio raíz adicional.

## Incluye
- Todas las bases de código de v0.6 con las correcciones de funcionalidad v0.8 incluidas (estados automáticos, cálculo de horas, cédulas por evento, confirmación de cambios sin guardar, selector anual y encabezados), más el ajuste de tablas v0.7.
- Paleta solicitada de 12 muestras aplicada a `ui/style.qss` y `ui/login.qss`.
- Logo PEMEX suministrado por el usuario sin alteración del archivo original: `assets/pemex-logo.ico`.
- Copia `assets/pemex-logo.png` del icono original para mostrarlo en Qt Designer.
- Icono de ventana y barra de tareas desde `main.py`, y el logotipo visible en el inicio de sesión y la ventana principal mediante `logica/identidad_visual.py`.

## Instalación
1. **Respalda el estado actual**: cierra la aplicación; revisa `git status` y haz un commit de seguridad. Guarda además tu respaldo de MySQL vigente.
2. Extrae el ZIP y copia **el contenido**, carpetas y archivos, sobre `C:\Users\crist\Proyecto-Pemexxx`.
3. Mantén intactos `.git/`, `.env`, `.venv/` y tus respaldos. Este ZIP no los incluye. Si ya personalizaste archivos `.ui` o `.py`, revisa diferencias antes de sobreescribirlos.
4. En VS Code, con el repositorio abierto, ejecuta:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.vista_previa_ui
```

5. Tras revisar la interfaz en modo vista previa (no consulta MySQL):

```powershell
.\.venv\Scripts\python.exe main.py
```

6. Desde Qt Designer puedes abrir `ui/main.ui` y `ui/login.ui`. Los pixmaps referencian `../assets/pemex-logo.png` por ruta relativa.

## Notas de seguridad y alcance
- Este paquete **no realiza migraciones SQL**. Si tu BD aún no tiene el esquema v0.6, usa el SQL de migración correspondiente con un respaldo previo, no un esquema nuevo.
- Los colores HEX son aproximaciones obtenidas de la imagen de referencia, no equivalencias oficiales Pantone.
- Se respetan los estados y los datos existentes: es un cambio de código y estilos, no de registros.
- No incluye credenciales ni archivos de datos reales; el logo es el que proporcionaste.
- Revisión realizada: sintaxis de Python, integridad XML de Qt Designer, estructura de recursos. Falta prueba visual/ejecución completa en tu PC y verificación de integración con tu repositorio exacto.
