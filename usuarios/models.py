from django.db import models
from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Dirección")

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else self.username

    class Meta:
        ordering = ["username"]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
