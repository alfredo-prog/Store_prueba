from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from inventario.models import Producto
from clientes.models import Cliente
from django.utils import timezone

Usuario = get_user_model()


class Venta(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('CONFIRMADO', 'Confirmado'),
        ('ANULADO', 'Anulado'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('QR', 'QR / Transferencia'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cliente")
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='BORRADOR', verbose_name="Estado")
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subtotal")
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Descuento")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total")
    
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True, verbose_name="Método de pago")
    monto_recibido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Monto recibido")
    cambio = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Cambio")

    def clean(self):
        if self.estado == 'CONFIRMADO' and not self.metodo_pago:
            raise ValidationError("Debe seleccionar un método de pago para confirmar la venta")
        
        if self.metodo_pago == 'EFECTIVO':
            if not self.monto_recibido or self.monto_recibido < self.total:
                raise ValidationError("El monto recibido debe ser mayor o igual al total")
            self.cambio = self.monto_recibido - self.total
        else:
            self.cambio = None

    def calcular_totales(self):
        subtotal_general = Decimal('0')
        descuento_general = Decimal('0')
        
        for detalle in self.detalles.all():
            bruto = detalle.precio_unitario * detalle.cantidad
            descuento_detalle = bruto * (detalle.descuento_porcentaje / Decimal('100'))
            subtotal_general += bruto
            descuento_general += descuento_detalle
        
        self.subtotal = subtotal_general
        self.descuento = descuento_general
        self.total = subtotal_general - descuento_general
        
        if self.pk:
            super().save(update_fields=['subtotal', 'descuento', 'total'])

    @staticmethod
    def sincronizar_stock_catalogo(producto_inventario):
        """Sincroniza el stock entre inventario y catálogo"""
        try:
            from inventario.models import Producto
            producto_catalogo = Producto.objects.filter(codigo=producto_inventario.codigo).first()
            if producto_catalogo:
                producto_catalogo.stock = producto_inventario.stock
                producto_catalogo.save(update_fields=['stock'])
                print(f"✅ Stock sincronizado: {producto_inventario.nombre} -> {producto_inventario.stock}")
                return True
            else:
                print(f"⚠️ Producto no encontrado en catálogo: {producto_inventario.codigo}")
                return False
        except Exception as e:
            print(f"❌ Error sincronizando catálogo: {e}")
            return False

    def aplicar_movimiento_stock(self):
        for detalle in self.detalles.all():
            producto = detalle.producto
            stock_anterior = producto.stock
            
            # Actualizar stock en inventario
            if self.estado == 'CONFIRMADO':
                if producto.stock < detalle.cantidad:
                    raise ValidationError(f"No hay suficiente stock de {producto.nombre}. Stock disponible: {producto.stock}")
                producto.stock -= detalle.cantidad
            elif self.estado == 'ANULADO':
                producto.stock += detalle.cantidad
            
            producto.save(update_fields=['stock'])
            
            # Sincronizar con catálogo
            sincronizado = Venta.sincronizar_stock_catalogo(producto)
            
            # Logging del movimiento
            accion = "DESCONTADO" if self.estado == 'CONFIRMADO' else "DEVUELTO"
            print(f"📦 Stock {accion}: {producto.nombre} | Anterior: {stock_anterior} | Actual: {producto.stock} | Catálogo: {'✅' if sincronizado else '❌'}")

    def save(self, *args, **kwargs):
        estado_anterior = None
        if self.pk:
            estado_anterior = Venta.objects.get(pk=self.pk).estado
        
        super().save(*args, **kwargs)
        
        # Solo aplicar movimiento de stock si el estado cambia y no se ha procesado manualmente
        if estado_anterior != self.estado:
            if self.estado in ['CONFIRMADO', 'ANULADO']:
                # Verificar si el stock ya fue descontado (evitar doble procesamiento)
                stock_ya_procesado = False
                if hasattr(self, '_stock_procesado'):
                    stock_ya_procesado = self._stock_procesado
                
                if not stock_ya_procesado:
                    self.calcular_totales()
                    self.aplicar_movimiento_stock()

    def __str__(self):
        return f"Venta #{self.id}"

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles", verbose_name="Venta")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name="Producto")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio unitario")
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="% Descuento")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subtotal")

    def clean(self):
        if self.descuento_porcentaje > 100:
            raise ValidationError("El descuento no puede ser mayor a 100%")
        if self.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")

    def save(self, *args, **kwargs):
        if self.precio_unitario is None or self.cantidad is None:
            self.subtotal = 0
        else:
            bruto = self.precio_unitario * self.cantidad
            descuento = bruto * (self.descuento_porcentaje / Decimal('100'))
            self.subtotal = bruto - descuento
        super().save(*args, **kwargs)
        
        if self.venta:
            self.venta.calcular_totales()

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"


class Proforma(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('CONFIRMADA', 'Confirmada'),
        ('CONVERTIDA_A_VENTA', 'Convertida a Venta'),
        ('ANULADA', 'Anulada'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('QR', 'QR'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name="Número de Proforma")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cliente")
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR', verbose_name="Estado")
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subtotal")
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Descuento")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total")
    
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True, verbose_name="Método de pago")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    def save(self, *args, **kwargs):
        if not self.numero:
            # Generar número automático
            ultima_proforma = Proforma.objects.all().order_by('-id').first()
            if ultima_proforma:
                ultimo_numero = int(ultima_proforma.numero.split('-')[1]) if '-' in ultima_proforma.numero else 0
                self.numero = f"PROF-{ultimo_numero + 1:04d}"
            else:
                self.numero = "PROF-0001"
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        subtotal_general = Decimal('0')
        descuento_general = Decimal('0')
        
        for item in self.items.all():
            subtotal_item = item.precio_unitario * item.cantidad
            subtotal_general += subtotal_item
        
        self.subtotal = subtotal_general
        self.descuento = descuento_general
        self.total = subtotal_general - descuento_general
        
        if self.pk:
            super().save(update_fields=['subtotal', 'descuento', 'total'])
    
    def convertir_a_venta(self):
        if self.estado == 'CONVERTIDA_A_VENTA':
            return None
        
        # Crear venta desde la proforma
        venta = Venta.objects.create(
            cliente=self.cliente,
            metodo_pago=self.metodo_pago,
            subtotal=self.subtotal,
            descuento=self.descuento,
            total=self.total
        )
        
        # Transferir items
        for item in self.items.all():
            DetalleVenta.objects.create(
                venta=venta,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                descuento_porcentaje=item.descuento_porcentaje
            )
        
        # Actualizar estado de proforma
        self.estado = 'CONVERTIDA_A_VENTA'
        self.save()
        
        return venta
    
    def __str__(self):
        return f"Proforma #{self.numero}"
    
    class Meta:
        verbose_name = "Proforma"
        verbose_name_plural = "Proformas"
        ordering = ['-fecha']


class ProformaItem(models.Model):
    proforma = models.ForeignKey(Proforma, on_delete=models.CASCADE, related_name="items", verbose_name="Proforma")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name="Producto")
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio unitario")
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="% Descuento")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Subtotal")
    
    def save(self, *args, **kwargs):
        if self.precio_unitario is None or self.cantidad is None:
            self.subtotal = 0
        else:
            bruto = self.precio_unitario * self.cantidad
            descuento = bruto * (self.descuento_porcentaje / Decimal('100'))
            self.subtotal = bruto - descuento
        super().save(*args, **kwargs)
        
        if self.proforma:
            self.proforma.calcular_totales()
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"
    
    class Meta:
        verbose_name = "Item de Proforma"
        verbose_name_plural = "Items de Proforma"

