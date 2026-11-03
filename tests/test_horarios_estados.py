import unittest
from datetime import date,datetime,time
from logica.reglas import calcular_horas_programadas,validar_horas_evento,estado_evento


class ValidacionEventoTest(unittest.TestCase):
    def test_24_horas_tres_dias(self):
        self.assertEqual(calcular_horas_programadas(
            date(2026,10,19),date(2026,10,21),time(9),time(17)),24)
        self.assertEqual(validar_horas_evento(
            date(2026,10,19),date(2026,10,21),time(9),time(17),'24'),24)

    def test_con_fin_de_semana_se_omiten_sabado_domingo(self):
        self.assertEqual(calcular_horas_programadas(
            date(2026,10,23),date(2026,10,26),time(8),time(16)),16)

    def test_horas_no_coinciden(self):
        with self.assertRaisesRegex(ValueError,'suman 24'):
            validar_horas_evento(date(2026,10,19),date(2026,10,21),time(9),time(17),'23')

    def test_sin_horas_invalidas(self):
        with self.assertRaises(ValueError):
            calcular_horas_programadas(date(2026,10,19),date(2026,10,21),time(17),time(9))
        with self.assertRaises(ValueError):
            calcular_horas_programadas(date(2026,10,17),date(2026,10,19),time(9),time(17))

    def test_estados(self):
        inicio=date(2026,10,19); fin=date(2026,10,21)
        self.assertEqual(estado_evento(inicio,fin,time(9),time(17),ahora=datetime(2026,10,19,8,59)),'PROGRAMADO')
        self.assertEqual(estado_evento(inicio,fin,time(9),time(17),ahora=datetime(2026,10,19,9)),'EN_CURSO')
        self.assertEqual(estado_evento(inicio,fin,time(9),time(17),ahora=datetime(2026,10,21,17)),'FINALIZADO')
        self.assertEqual(estado_evento(inicio,fin,time(9),time(17),cancelado=True,
                                       ahora=datetime(2026,10,19,12)),'CANCELADO')


if __name__=='__main__': unittest.main()
