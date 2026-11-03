-- Comprobación no destructiva de la actualización v0.6
USE sistema_capacitacion_cangrejera;
SELECT id,codigo,nombre FROM roles ORDER BY id;
SHOW COLUMNS FROM cursos;
SHOW COLUMNS FROM usuarios;
SELECT id,nombre,clave_evento,clasificacion_evento,duracion_horas,YEAR(fecha_inicio) AS anio
FROM cursos ORDER BY id DESC LIMIT 15;
SELECT u.id,u.nombre_usuario,COALESCE(r.codigo,'SIN_ROL') AS rol
FROM usuarios u LEFT JOIN roles r ON r.id=u.rol_id;
SELECT COUNT(*) AS detalles_registrados FROM trabajador_detalle;
SELECT COUNT(*) AS cambios_de_nivel FROM historial_niveles;
