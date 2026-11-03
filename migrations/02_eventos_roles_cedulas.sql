-- MIGRACION v0.6. EJECUTAR DESPUES DE HACER RESPALDO.
-- Repetible para tablas/columnas previstas. Conserva todos los datos existentes.
-- No cambia el nombre fisico 'cursos' (en pantalla se muestra 'Eventos').
USE sistema_capacitacion_cangrejera;

CREATE TABLE IF NOT EXISTS roles (
 id TINYINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 codigo VARCHAR(20) NOT NULL UNIQUE,
 nombre VARCHAR(60) NOT NULL,
 descripcion VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
INSERT INTO roles(codigo,nombre,descripcion) VALUES
 ('ADMIN','Administrador','Usuarios, respaldos y todas las funciones'),
 ('CAPTURA','Capturista','Registra trabajadores, eventos, inscripciones y cédulas'),
 ('CONSULTA','Consulta y reportes','Solo consulta y generación de reportes')
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre),descripcion=VALUES(descripcion);

DELIMITER $$
DROP PROCEDURE IF EXISTS sp_migrar_v06$$
CREATE PROCEDURE sp_migrar_v06()
BEGIN
 IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='usuarios' AND column_name='rol_id') THEN
   ALTER TABLE usuarios ADD COLUMN rol_id TINYINT UNSIGNED NULL AFTER password_hash;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.referential_constraints WHERE constraint_schema=DATABASE() AND table_name='usuarios' AND constraint_name='fk_usuarios_rol') THEN
   ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_rol FOREIGN KEY(rol_id) REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='cursos' AND column_name='clave_evento') THEN
   ALTER TABLE cursos ADD COLUMN clave_evento CHAR(8) NULL AFTER id;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='cursos' AND column_name='clasificacion_evento') THEN
   ALTER TABLE cursos ADD COLUMN clasificacion_evento ENUM('CONTRACTUAL','CONFIANZA','ASCENSO') NULL AFTER modalidad;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='cursos' AND column_name='duracion_horas') THEN
   ALTER TABLE cursos ADD COLUMN duracion_horas DECIMAL(6,2) NULL AFTER fecha_fin;
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='cursos' AND index_name='uq_cursos_clave_evento') THEN
   ALTER TABLE cursos ADD UNIQUE INDEX uq_cursos_clave_evento (clave_evento);
 END IF;
 IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=DATABASE() AND table_name='cursos' AND constraint_name='chk_cursos_clave_8') THEN
   ALTER TABLE cursos ADD CONSTRAINT chk_cursos_clave_8 CHECK (clave_evento IS NULL OR REGEXP_LIKE(clave_evento,'^[0-9]{8}$'));
 END IF;
END$$
DELIMITER ;
CALL sp_migrar_v06();
DROP PROCEDURE IF EXISTS sp_migrar_v06;

-- No otorgamos ADMIN automáticamente a cuentas anteriores: asignarlas
-- explícitamente con scripts/configurar_usuarios.py desde el equipo autorizado.
CREATE TABLE IF NOT EXISTS trabajador_detalle (
 trabajador_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
 curp CHAR(18) NULL,
 nombres VARCHAR(100) NULL,
 apellido_paterno VARCHAR(80) NULL,
 apellido_materno VARCHAR(80) NULL,
 centro_trabajo VARCHAR(160) NULL,
 clave_centro_trabajo VARCHAR(30) NULL,
 subsidiaria VARCHAR(150) NULL,
 gerencia VARCHAR(150) NULL,
 clave_departamento VARCHAR(30) NULL,
 categoria_base VARCHAR(120) NULL,
 nivel VARCHAR(40) NULL,
 turno VARCHAR(60) NULL,
 tipo_plaza ENUM('PLANTA','TRANSITORIO','CONFIANZA','SINDICALIZADO') NULL,
 jefe_inmediato VARCHAR(160) NULL,
 extension VARCHAR(30) NULL,
 entidad_federativa VARCHAR(100) NULL,
 municipio VARCHAR(120) NULL,
 nivel_estudios VARCHAR(50) NULL,
 carrera VARCHAR(160) NULL,
 documento_probatorio VARCHAR(50) NULL,
 anio_documento SMALLINT UNSIGNED NULL,
 institucion_tipo ENUM('PUBLICA','PRIVADA') NULL,
 discapacidad VARCHAR(100) NULL,
 estado_civil VARCHAR(30) NULL,
 hijos_dependientes TINYINT UNSIGNED NULL,
 actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 CONSTRAINT fk_detalle_trabajador FOREIGN KEY (trabajador_id) REFERENCES trabajadores(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Cambios de nivel tras finalizar un evento de ASCENSO.
CREATE TABLE IF NOT EXISTS historial_niveles (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 trabajador_id BIGINT UNSIGNED NOT NULL,
 inscripcion_id BIGINT UNSIGNED NOT NULL,
 nivel_anterior VARCHAR(40) NULL,
 nivel_nuevo VARCHAR(40) NOT NULL,
 usuario_id BIGINT UNSIGNED NOT NULL,
 aplicado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_niveles_trabajador FOREIGN KEY(trabajador_id) REFERENCES trabajadores(id) ON DELETE RESTRICT,
 CONSTRAINT fk_niveles_inscripcion FOREIGN KEY(inscripcion_id) REFERENCES inscripciones(id) ON DELETE RESTRICT,
 CONSTRAINT fk_niveles_usuario FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Instalaciones antiguas sin tabla de historial de bajas.
CREATE TABLE IF NOT EXISTS bajas_inscripciones (
 id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
 inscripcion_id BIGINT UNSIGNED NOT NULL,
 fecha_baja DATETIME NOT NULL,
 motivo_baja VARCHAR(500) NULL,
 usuario_id BIGINT UNSIGNED NULL,
 registrado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 KEY idx_bajas_inscripcion(inscripcion_id),
 CONSTRAINT fk_bajas_inscripcion FOREIGN KEY(inscripcion_id) REFERENCES inscripciones(id) ON DELETE RESTRICT,
 CONSTRAINT fk_bajas_usuario FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Resguardo del historial de las bajas; el trigger es recreado sin duplicar filas.
DROP TRIGGER IF EXISTS trg_guardar_baja_inscripcion;
DELIMITER $$
CREATE TRIGGER trg_guardar_baja_inscripcion
AFTER UPDATE ON inscripciones FOR EACH ROW
BEGIN
 IF OLD.estado='INSCRITO' AND NEW.estado='BAJA' THEN
  INSERT INTO bajas_inscripciones(inscripcion_id,fecha_baja,motivo_baja,usuario_id)
  VALUES(NEW.id,COALESCE(NEW.fecha_baja,NOW()),NEW.motivo_baja,NEW.usuario_baja_id);
 END IF;
END$$
DELIMITER ;

-- No se redefinen vistas anteriores: conservan compatibilidad con la versión previa.
SELECT r.codigo, r.nombre FROM roles r ORDER BY r.id;
SELECT COUNT(*) AS eventos_sin_clave FROM cursos WHERE clave_evento IS NULL;
SELECT COUNT(*) AS usuarios_sin_rol FROM usuarios WHERE rol_id IS NULL;
