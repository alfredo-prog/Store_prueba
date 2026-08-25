from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre completo")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Dirección")
    email = models.EmailField(blank=True, null=True, unique=True, verbose_name="Correo electrónico")

    def __str__(self):
        return f"{self.nombre} ({self.email})" if self.email else self.nombre

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
