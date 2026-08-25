from django.db import models
from django.utils import timezone
from proveedores.models import Proveedor
from inventario.models import Producto

class Compra(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('QR', 'QR / Transferencia'),
    ]
    
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, verbose_name="Proveedor")
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha de compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total de compra")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE', verbose_name="Estado")
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='EFECTIVO', verbose_name="Método de pago")

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor.nombre}"

    def calcular_total(self):
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.total = total
        self.save()

    def actualizar_inventario(self):
        """Actualiza el inventario cuando la compra se completa"""
        for detalle in self.detalles.all():
            producto = detalle.producto
            
            # ⚠️ evitar duplicación
            if not hasattr(detalle, '_stock_actualizado'):
                producto.stock += detalle.cantidad
                producto.save()
                detalle._stock_actualizado = True
                
                print(f"Stock actualizado: {producto.nombre} +{detalle.cantidad} = {producto.stock}")
        return True

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not is_new:
            compra_anterior = Compra.objects.get(pk=self.pk)
            estado_anterior = compra_anterior.estado
        else:
            estado_anterior = None

        super().save(*args, **kwargs)

        # 🔥 CASO 1: creación directa en COMPLETADO
        if is_new and self.estado == 'COMPLETADO':
            self.actualizar_inventario()

        # 🔥 CASO 2: cambio de estado a COMPLETADO
        elif estado_anterior != 'COMPLETADO' and self.estado == 'COMPLETADO':
            self.actualizar_inventario()

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles", verbose_name="Compra")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, verbose_name="Producto")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio unitario")

    @property
    def subtotal(self):
        cantidad = self.cantidad or 0
        precio_unitario = self.precio_unitario or 0
        return cantidad * precio_unitario

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    class Meta:
        verbose_name = "Detalle de compra"
        verbose_name_plural = "Detalles de compra"