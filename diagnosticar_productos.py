#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

from inventario.models import Producto
from catalogo.models import Category

def diagnosticar_productos():
    print("🔍 DIAGNÓSTICO DE PRODUCTOS")
    print("=" * 50)
    
    # 1. Contar productos totales
    total_productos = Producto.objects.count()
    print(f"📊 Total productos en BD: {total_productos}")
    
    # 2. Contar por estado
    activos = Producto.objects.filter(activo=True).count()
    inactivos = Producto.objects.filter(activo=False).count()
    print(f"✅ Productos activos: {activos}")
    print(f"❌ Productos inactivos: {inactivos}")
    
    # 3. Verificar categorías
    categorias = Category.objects.count()
    print(f"📁 Total categorías: {categorias}")
    
    # 4. Mostrar primeros 10 productos con su estado
    print("\n📋 Primeros 10 productos:")
    for i, producto in enumerate(Producto.objects.all()[:10], 1):
        estado = "✅ Activo" if producto.activo else "❌ Inactivo"
        categoria = producto.categoria.name if producto.categoria else "Sin categoría"
        print(f"  {i}. {producto.nombre[:30]} - {estado} - {categoria} - Stock: {producto.stock}")
    
    # 5. Si hay productos inactivos, preguntar si activarlos
    if inactivos > 0:
        print(f"\n⚠️  Hay {inactivos} productos inactivos")
        print("¿Deseas activar todos los productos? (y/n)")
        respuesta = input().lower()
        
        if respuesta == 'y':
            Producto.objects.filter(activo=False).update(activo=True)
            print("✅ Todos los productos han sido activados")
        else:
            print("❌ No se activaron los productos")
    
    # 6. Verificar productos sin categoría
    sin_categoria = Producto.objects.filter(categoria__isnull=True).count()
    if sin_categoria > 0:
        print(f"\n⚠️  Hay {sin_categoria} productos sin categoría")
    
    print("\n🎯 DIAGNÓSTICO COMPLETADO")
    print(f"📊 Resumen: {total_productos} totales, {activos} activos, {inactivos} inactivos")

if __name__ == "__main__":
    diagnosticar_productos()
