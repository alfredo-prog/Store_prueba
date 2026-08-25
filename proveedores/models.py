from django.db import models

class Proveedor(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre empresa")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, unique=True, verbose_name="Correo electrónico")
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Dirección")

    def __str__(self):
        return f"{self.nombre} ({self.email})" if self.email else self.nombre

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"