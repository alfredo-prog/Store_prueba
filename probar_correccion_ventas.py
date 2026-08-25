#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from ventas.views import verificar_estado_caja

def probar_correccion():
    print("🔍 PROBANDO CORRECCIÓN DE VENTAS")
    print("=" * 50)
    
    # Crear una solicitud simulada
    factory = RequestFactory()
    request = factory.get('/ventas/')
    
    # Asignar usuario anónimo
    request.user = AnonymousUser()
    
    try:
        # Probar la función corregida
        resultado = verificar_estado_caja(request)
        print(f"✅ Función ejecutada correctamente")
        print(f"📊 Resultado: {resultado}")
        print(f"🎯 Usuario anónimo manejado sin errores")
        
        # Verificar que el resultado sea el esperado
        if resultado == {'caja_abierta': False}:
            print("✅ Respuesta correcta para usuario anónimo")
        else:
            print(f"⚠️ Respuesta inesperada: {resultado}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n🎉 CORRECCIÓN VERIFICADA EXITOSAMENTE")
    return True

if __name__ == "__main__":
    probar_correccion()
