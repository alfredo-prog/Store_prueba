from django.db import models
from proveedores.models import Proveedor
from catalogo.models import Category

class Producto(models.Model):
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre del producto")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Proveedor")
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio de costo")
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio de venta")
    stock = models.IntegerField(default=0, verbose_name="Stock")
    stock_minimo = models.PositiveIntegerField(default=0, verbose_name="Stock mínimo")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    categoria = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
    # Campos adicionales para compatibilidad con catálogo
    codigo = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Código interno (SKU)")
    codigo_barras = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Código de barras")
    imagen = models.ImageField(upload_to="productos/", blank=True, null=True, verbose_name="Imagen del producto")
    porcentaje_ganancia = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, verbose_name="% Ganancia")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de actualización")
    
    # Propiedades para compatibilidad con código en inglés
    @property
    def sale_price(self):
        return self.precio_venta
    
    @property
    def purchase_price(self):
        return self.precio_costo
    
    @property
    def name(self):
        return self.nombre
    
    @property
    def code(self):
        return self.codigo or f"PROD-{self.id:04d}"
    
    @property
    def barcode(self):
        return self.codigo_barras or self.codigo
    
    @property
    def min_stock(self):
        return self.stock_minimo
    
    @property
    def cost_price(self):
        return self.precio_costo
    
    @property
    def category(self):
        return self.categoria
    
    @property
    def is_active(self):
        return self.activo
    
    @property
    def created_at(self):
        return self.fecha_creacion
    
    @property
    def updated_at(self):
        return self.fecha_actualizacion
    
    def save(self, *args, **kwargs):
        # Generar código automáticamente si no existe.
        # Si no hay código y el objeto aún no tiene ID, guardar primero para obtener el ID.
        if self.codigo:
            super().save(*args, **kwargs)
            return

        if self.pk:
            self.codigo = f"PROD-{self.pk:04d}"
            super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"PROD-{self.id:04d}"
            Producto.objects.filter(pk=self.pk).update(codigo=self.codigo)

    def __str__(self):
        categoria_nombre = self.categoria.name if self.categoria else "Sin categoría"
        return f"{self.nombre} - Stock: {self.stock} - {categoria_nombre}"

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"