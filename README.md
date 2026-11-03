# Sistema de Capacitación Cangrejera — actualización v0.6

Código Python/PySide6 + MySQL. **No es otro proyecto**: el contenido de este paquete debe copiarse **dentro** de la carpeta del repositorio existente `Proyecto-Pemexxx`, sin sustituir `.git`, `.venv` ni `.env`.

## Procedencia y alcance

Se integró a partir de los paquetes del proyecto disponibles en esta conversación: estructura v0.2, login v0.3 y rediseño/acceso rápido v0.5. No se ha podido acceder en vivo al repositorio de GitHub; revisa `git diff` antes del commit por si realizaste otros cambios locales. **No se ha hecho ningún push a GitHub ni se ha ejecutado MySQL en tu computadora desde aquí.**

## Instalación (en este orden)

1. **Haz un nuevo respaldo** desde PowerShell/Workbench antes de la migración. Conserva el respaldo fuera de Git.
2. Cierra la aplicación.
3. En MySQL Workbench abre y ejecuta **todo** `migrations/02_eventos_roles_cedulas.sql` en la base `sistema_capacitacion_cangrejera`. Esta migración no elimina trabajadores, eventos, inscripciones, usuarios ni cédulas existentes.
4. Copia el contenido del paquete v0.6 dentro de `C:\Users\crist\Proyecto-Pemexxx`, preservando `.git`, `.venv` y `.env`. No abras la carpeta ZIP como proyecto independiente.
5. En VS Code (terminal en la raíz del repo):

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

6. **Alta inicial de cuentas** desde la misma computadora autorizada:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.configurar_usuarios
   ```

   El script solicita cuentas ADMIN y CAPTURA; puedes **asignar uno de esos roles a una cuenta preexistente** o crearla. Las cuentas antiguas **sin rol no podrán acceder** hasta que se les asigne uno. El tercer rol CONSULTA está definido para crear la cuenta posteriormente desde la pantalla Usuarios.

7. Inicia desde VS Code:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

   O con doble clic en `Iniciar_Sistema.bat`.

8. Comprueba el año, crea un evento de prueba con clave de ocho dígitos, inscribe a un trabajador ficticio, prueba un solapamiento, genera cédula, filtra reportes y cambia de usuario para verificar permisos.

## Funciones incorporadas

- Menú **Eventos** (la tabla de MySQL **sigue siendo `cursos`** para compatibilidad).
- Año de gestión en selector, en título y filtros de estadísticas, eventos, inscripciones y reportes. Se agrupa según el **año de inicio** del evento.
- Clave del evento de **exactamente ocho dígitos**, guardada como CHAR(8) y única. Se conservan ceros iniciales. Los eventos antiguos mantienen NULL hasta que se les asigne una clave válida.
- Tipo Cangrejera / Gas / Seguridad, modalidad Presencial / En línea, clasificación Contractual / Confianza / Ascenso, duración.
- Una persona puede tener historial de múltiples eventos, pero no dos inscripciones vigentes en eventos con **fechas superpuestas**. La validación se hace en una transacción desde la aplicación (otros clientes SQL no están sujetos a esta regla si escriben directamente en las tablas).
- Un evento ASCENSO finalizado permite capturar **Nivel** nuevo con confirmación y trazabilidad en `historial_niveles`. El nuevo nivel **no se asigna automáticamente** al inscribirse.
- Tres roles: ADMIN (todo, usuarios y respaldos), CAPTURA (trabajadores, eventos, inscripciones, cédulas), CONSULTA (búsqueda, filtros, reportes PDF). El control de permisos se implementa en Python además de los botones.
- Datos detallados de trabajadores en `trabajador_detalle`, separados del registro básico, para autocompletar la cédula individual. Los datos no registrados salen en blanco. Cédulas en `salidas/cedulas/` (ignorado por Git).
- Reportes filtrables por año, tipo, modalidad, clasificación y estado, con resumen, barras visuales y PDF.
- Mensajes de validación: datos faltantes, clave, duplicados, fechas, solapamiento y acceso denegado.
- Iniciador Windows `Iniciar_Sistema.bat`.

## Modelo de roles

| Acción | ADMIN | CAPTURA | CONSULTA |
|---|---|---|---|
| Consultar información | Sí | Sí | Sí |
| Reportes y PDF de reportes | Sí | Sí | Sí |
| Trabajadores, eventos e inscripciones | Sí | Sí | No |
| Cédulas y detalle del trabajador | Sí | Sí | No |
| Cambios de nivel por Ascenso | Sí | Sí | No |
| Usuarios y respaldos | Sí | No | No |

**Cuentas iniciales previstas: 2** (ADMIN y CAPTURA). El rol CONSULTA está listo, pero su cuenta no se crea automáticamente.

## Lo que sigue sin especificarse

Las modalidades y clasificaciones **no equivalen a tarifas**. Un evento CONTRACTUAL queda identificado y su duración registrada, pero todavía no se calculan pagos monetarios al instructor. En eventos CONFIANZA se identifica la clasificación, sin sumar horas pagadas al trabajador; falta definir reglas exactas de nómina. La cédula generada usa los campos de la hoja ejemplo del usuario, con formato propio para impresión y firma, no es una reproducción idéntica del documento corporativo.

Para datos reales (CURP, salud/discapacidad y personales), usa usuarios autorizados, respaldos protegidos y una cuenta de MySQL con permisos mínimos en lugar de root; no subas datos ni PDFs a repositorios públicos.

## Archivos principales

- `migrations/02_eventos_roles_cedulas.sql`: actualización de MySQL, repetible en estructura.
- `ui/main.ui`: pantallas en Qt Designer, navegable con menú lateral.
- `ui/login.ui`, `ui/detalle_trabajador.ui`: login y captura complementaria.
- `logica/sistema.py`: eventos de botones, navegación por año, permisos.
- `logica/cursos.py`: operaciones de eventos; `logica/inscripciones.py`: inscribir, bajas y ascensos.
- `logica/cedulas.py`: PDF individual, detalle; `logica/reportes.py`: filtros, gráfico y PDF.
- `logica/usuarios.py`: altas, activación/desactivación y respaldos.
- `logica/reglas.py`: validaciones puras reutilizables.
- `scripts/configurar_usuarios.py`: 2 cuentas iniciales con Argon2id.
- `tests/test_reglas.py`: pruebas automáticas sin Qt ni MySQL.

Prueba rápida estática:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para subir a GitHub tras comprobarlo:

```powershell
git status
git diff
git add .
git status
git commit -m "Agregar gestion anual de eventos, roles, cedulas y reportes"
git push origin main
```

Comprueba que **`.env`, `.venv`, PDFs y respaldos no estén en `git status`** antes de confirmar.
