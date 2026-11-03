import unittest
from datetime import date
from logica.reglas import validar_clave_evento,validar_duracion,rango_se_cruza,tiene_permiso

class ReglasTests(unittest.TestCase):
    def test_clave_exacta(self):
        self.assertEqual(validar_clave_evento('00001234'),'00001234')
        for clave in ['1234567','123456789','12345abc','',' 12345678']:
            with self.subTest(clave=clave),self.assertRaises(ValueError):validar_clave_evento(clave)
    def test_duracion(self):
        self.assertEqual(str(validar_duracion('80')), '80')
        for v in ['hola','-5','0','nan']:
            with self.subTest(v=v),self.assertRaises(ValueError):validar_duracion(v)
    def test_solapamiento(self):
        self.assertTrue(rango_se_cruza(date(2026,10,1),date(2026,10,4),
                                       date(2026,10,4),date(2026,10,8)))
        self.assertFalse(rango_se_cruza(date(2026,10,1),date(2026,10,3),
                                       date(2026,10,4),date(2026,10,8)))
    def test_roles(self):
        for rol in ('ADMIN','CAPTURA','CONSULTA'):
            self.assertTrue(tiene_permiso(rol,'consulta'))
            self.assertTrue(tiene_permiso(rol,'reporte'))
        for op in ('captura','cedula'):
            self.assertTrue(tiene_permiso('ADMIN',op))
            self.assertTrue(tiene_permiso('CAPTURA',op))
            self.assertFalse(tiene_permiso('CONSULTA',op))
        self.assertTrue(tiene_permiso('ADMIN','admin'))
        self.assertFalse(tiene_permiso('CAPTURA','admin'))
        self.assertFalse(tiene_permiso('CONSULTA','admin'))
