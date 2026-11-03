"""Reglas del sistema: sin dependencia de la interfaz."""
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

ROLES = ('ADMIN', 'CAPTURA', 'CONSULTA')
CLASIFICACIONES = ('CONTRACTUAL', 'CONFIANZA', 'ASCENSO')


def validar_clave_evento(clave):
    if not re.fullmatch(r'[0-9]{8}', str(clave)):
        raise ValueError('La clave del evento debe contener exactamente 8 dígitos numéricos.')
    return str(clave)


def validar_duracion(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError('La duración debe ser un número de horas válido.') from None
    if not n.is_finite() or not (Decimal('0') < n <= Decimal('9999.99')):
        raise ValueError('La duración debe ser mayor que cero y menor a 10000 horas.')
    return n


def calcular_horas_programadas(inicio: date, fin: date, hora_inicio: time, hora_fin: time):
    """Horario diario fijo de lunes a viernes, sin contemplar feriados.

    Las horas se consideran tiempo transcurrido, sin descuentos automáticos
    por comida/recesos. El horario no puede cruzar la medianoche.
    """
    if fin < inicio:
        raise ValueError('La fecha de término no puede ser anterior al inicio.')
    if inicio.weekday() >= 5 or fin.weekday() >= 5:
        raise ValueError('El evento debe iniciar y terminar entre lunes y viernes.')
    hoy = inicio
    laborales = 0
    while hoy <= fin:
        if hoy.weekday() < 5:
            laborales += 1
        hoy += timedelta(days=1)
    segundos = (hora_fin.hour*3600 + hora_fin.minute*60 + hora_fin.second
                - hora_inicio.hour*3600 - hora_inicio.minute*60 - hora_inicio.second)
    if segundos <= 0:
        raise ValueError('La hora de término debe ser posterior a la de inicio en el mismo día.')
    return (Decimal(laborales) * Decimal(segundos) / Decimal(3600)).quantize(Decimal('0.01'))


def validar_horas_evento(inicio, fin, hora_inicio, hora_fin, duracion):
    calculadas = calcular_horas_programadas(inicio, fin, hora_inicio, hora_fin)
    declaradas = validar_duracion(duracion)
    if declaradas != calculadas:
        raise ValueError(f'La duración registrada es {declaradas:g} horas, pero el calendario '
                         f'y el horario de lunes a viernes suman {calculadas:g} horas. '
                         'Ajusta las fechas, las horas o la duración total.')
    return calculadas


def estado_evento(inicio: date, fin: date, hora_inicio: time | None,
                  hora_fin: time | None, cancelado=False, ahora=None):
    """Estado calculado a partir del calendario; cancelado no se revierte."""
    if cancelado:
        return 'CANCELADO'
    ahora = ahora or datetime.now()
    inicio_dt = datetime.combine(inicio, hora_inicio or time.min)
    fin_dt = datetime.combine(fin, hora_fin or time.max)
    if ahora < inicio_dt:
        return 'PROGRAMADO'
    if ahora >= fin_dt:
        return 'FINALIZADO'
    return 'EN_CURSO'


def rango_se_cruza(inicio1, fin1, inicio2, fin2):
    return inicio1 <= fin2 and fin1 >= inicio2


def tiene_permiso(rol, operacion):
    if rol == 'ADMIN':
        return True
    if operacion in ('consulta', 'reporte'):
        return rol in ('CAPTURA', 'CONSULTA')
    if operacion in ('captura', 'cedula'):
        return rol == 'CAPTURA'
    return False
