from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

Usuario = get_user_model()

class Caja(models.Model):
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]
    
    fecha_apertura = models.DateTimeField(default=timezone.now, verbose_name="Fecha de apertura")
    fecha_cierre = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de cierre")
    saldo_inicial_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo inicial efectivo")
    saldo_inicial_qr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo inicial QR")
    saldo_final_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo final efectivo")
    saldo_final_qr = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo final QR")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ABIERTA')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['-fecha_apertura']

    def __str__(self):
        return f"Caja #{self.id} - {self.fecha_apertura.date()} ({self.get_estado_display()})"

    @property
    def saldo_inicial_total(self):
        return self.saldo_inicial_efectivo + self.saldo_inicial_qr

    @property
    def saldo_final_total(self):
        return self.saldo_final_efectivo + self.saldo_final_qr

    @property
    def total_ingresos_efectivo(self):
        return self.movimientos.filter(tipo='INGRESO', metodo_pago='EFECTIVO').aggregate(
            total=models.Sum('monto'))['total'] or 0

    @property
    def total_ingresos_qr(self):
        return self.movimientos.filter(tipo='INGRESO', metodo_pago='QR').aggregate(
            total=models.Sum('monto'))['total'] or 0

    @property
    def total_egresos_efectivo(self):
        return self.movimientos.filter(tipo='EGRESO', metodo_pago='EFECTIVO').aggregate(
            total=models.Sum('monto'))['total'] or 0

    @property
    def total_egresos_qr(self):
        return self.movimientos.filter(tipo='EGRESO', metodo_pago='QR').aggregate(
            total=models.Sum('monto'))['total'] or 0

    @property
    def saldo_esperado_efectivo(self):
        return self.saldo_inicial_efectivo + self.total_ingresos_efectivo - self.total_egresos_efectivo

    @property
    def saldo_esperado_qr(self):
        return self.saldo_inicial_qr + self.total_ingresos_qr - self.total_egresos_qr

    @property
    def diferencia_efectivo(self):
        return self.saldo_final_efectivo - self.saldo_esperado_efectivo

    @property
    def diferencia_qr(self):
        return self.saldo_final_qr - self.saldo_esperado_qr

    def cerrar_caja(self, saldo_final_efectivo, saldo_final_qr, observaciones=''):
        self.saldo_final_efectivo = saldo_final_efectivo
        self.saldo_final_qr = saldo_final_qr
        self.fecha_cierre = timezone.now()
        self.estado = 'CERRADA'
        self.observaciones = observaciones
        self.save()


class MovimientoCaja(models.Model):
    TIPO_CHOICES = [
        ("INGRESO", "Ingreso"),
        ("EGRESO", "Egreso"),
    ]
    
    METODO_PAGO_CHOICES = [
        ("EFECTIVO", "Efectivo"),
        ("QR", "QR"),
        ("TRANSFERENCIA", "Transferencia"),
        ("TARJETA", "Tarjeta"),
    ]
    
    CATEGORIA_CHOICES = [
        ("VENTA", "Venta"),
        ("COMPRA", "Compra"),
        ("GASTO", "Gasto"),
        ("AJUSTE", "Ajuste"),
        ("OTRO", "Otro"),
    ]
    
    caja = models.ForeignKey(Caja, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    metodo_pago = models.CharField(max_length=15, choices=METODO_PAGO_CHOICES, default='EFECTIVO')
    categoria = models.CharField(max_length=10, choices=CATEGORIA_CHOICES, default='OTRO')
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    referencia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia")

    class Meta:
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo} - {self.monto} ({self.fecha.date()})"

    @property
    def tipo_display(self):
        return dict(self.TIPO_CHOICES).get(self.tipo, self.tipo)

    @property
    def metodo_pago_display(self):
        return dict(self.METODO_PAGO_CHOICES).get(self.metodo_pago, self.metodo_pago)
