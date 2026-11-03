import ast
import unittest
from datetime import date, time
from pathlib import Path
from xml.etree import ElementTree as ET
from logica.reglas import calcular_horas_programadas, validar_duracion

ROOT = Path(__file__).resolve().parent.parent

class VistaPreviaDuracionTest(unittest.TestCase):
    def test_ejemplo_24_horas(self):
        self.assertEqual(calcular_horas_programadas(
            date(2026,10,19), date(2026,10,21), time(9), time(17)),24)

    def test_fin_de_semana_no_cuenta(self):
        self.assertEqual(calcular_horas_programadas(
            date(2026,10,23), date(2026,10,26), time(9), time(17)),16)

    def test_horario_invalido(self):
        with self.assertRaises(ValueError):
            calcular_horas_programadas(date(2026,10,19),date(2026,10,19),time(17),time(9))

    def test_duracion_limites(self):
        with self.assertRaises(ValueError):
            validar_duracion('10000')

    def test_ui_duracion_solo_lectura(self):
        root=ET.parse(ROOT/'ui/main.ui').getroot()
        campos=[w for w in root.iter('widget') if w.attrib.get('name')=='txtDuracionHoras']
        self.assertEqual(len(campos),1)
        props={p.attrib.get('name'):p for p in campos[0].findall('property')}
        self.assertEqual(props['readOnly'].findtext('bool'),'true')

    def test_codigo_compila(self):
        for archivo in ('logica/cursos.py','logica/sistema.py'):
            ast.parse((ROOT/archivo).read_text(encoding='utf-8'))

    def test_preview_antes_de_insert_y_update(self):
        src=(ROOT/'logica/cursos.py').read_text(encoding='utf-8')
        guardar=src[src.index('    def guardar_curso('):src.index('    def cancelar_curso(')]
        self.assertLess(guardar.index('if not self._mostrar_vista_previa_evento('),guardar.index('INSERT INTO cursos'))
        self.assertLess(guardar.index('if not self._mostrar_vista_previa_evento('),guardar.index('UPDATE cursos'))

if __name__=='__main__': unittest.main()
