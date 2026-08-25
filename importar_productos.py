#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

from inventario.models import Producto
from catalogo.models import Category, Product

def importar_desde_catalogo():
    """Importar productos desde catalogo.models.Product hacia inventario.models.Producto"""
    print("🔄 IMPORTANDO PRODUCTOS DESDE CATÁLOGO")
    print("=" * 50)
    
    # Obtener todos los productos del catálogo
    productos_catalogo = Product.objects.all()
    print(f"📊 Productos en catálogo: {productos_catalogo.count()}")
    
    importados = 0
    actualizados = 0
    
    for prod_cat in productos_catalogo:
        # Buscar si ya existe en inventario
        prod_inventario = Producto.objects.filter(
            codigo=prod_cat.codigo
        ).first()
        
        if prod_inventario:
            # Actualizar producto existente
            prod_inventario.nombre = prod_cat.nombre
            prod_inventario.categoria = prod_cat.categoria
            prod_inventario.precio_costo = prod_cat.precio_costo
            prod_inventario.precio_venta = prod_cat.precio_venta
            prod_inventario.stock = prod_cat.stock
            prod_inventario.stock_minimo = prod_cat.stock_minimo
            prod_inventario.descripcion = prod_cat.descripcion
            prod_inventario.activo = prod_cat.activo
            prod_inventario.save()
            actualizados += 1
            print(f"✅ Actualizado: {prod_cat.nombre}")
        else:
            # Crear nuevo producto en inventario
            prod_inventario = Producto.objects.create(
                codigo=prod_cat.codigo,
                codigo_barras=prod_cat.codigo_barras or '',
                nombre=prod_cat.nombre,
                categoria=prod_cat.categoria,
                precio_costo=prod_cat.precio_costo,
                precio_venta=prod_cat.precio_venta,
                stock=prod_cat.stock,
                stock_minimo=prod_cat.stock_minimo,
                descripcion=prod_cat.descripcion,
                activo=prod_cat.activo
            )
            importados += 1
            print(f"➕ Importado: {prod_cat.nombre}")
    
    print(f"\n📊 RESUMEN:")
    print(f"➕ Importados: {importados}")
    print(f"✅ Actualizados: {actualizados}")
    print(f"📊 Total en inventario: {Producto.objects.count()}")

def crear_productos_ejemplo():
    """Crear productos de ejemplo si no hay datos"""
    print("\n🔧 CREANDO PRODUCTOS DE EJEMPLO")
    print("=" * 50)
    
    # Crear categorías si no existen
    categorias_data = [
        {"name": "Bebidas", "description": "Bebidas variadas"},
        {"name": "Alimentos", "description": "Productos alimenticios"},
        {"name": "Limpieza", "description": "Productos de limpieza"},
        {"name": "Snacks", "description": "Snacks y golosinas"},
    ]
    
    for cat_data in categorias_data:
        categoria, created = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={"description": cat_data["description"]}
        )
        if created:
            print(f"➕ Categoría creada: {categoria.name}")
    
    # Crear productos de ejemplo
    productos_data = [
        {"nombre": "Coca Cola 2L", "codigo": "CC001", "categoria": "Bebidas", "precio_costo": 8.50, "precio_venta": 12.00, "stock": 50},
        {"nombre": "Pepsi 2L", "codigo": "PP001", "categoria": "Bebidas", "precio_costo": 7.50, "precio_venta": 11.00, "stock": 45},
        {"nombre": "Fanta 2L", "codigo": "FF001", "categoria": "Bebidas", "precio_costo": 7.00, "precio_venta": 10.50, "stock": 30},
        {"nombre": "Papas Lays", "codigo": "PL001", "categoria": "Snacks", "precio_costo": 3.00, "precio_venta": 5.50, "stock": 100},
        {"nombre": "Doritos", "codigo": "DD001", "categoria": "Snacks", "precio_costo": 3.50, "precio_venta": 6.00, "stock": 80},
        {"nombre": "Arroz 5kg", "codigo": "AR001", "categoria": "Alimentos", "precio_costo": 25.00, "precio_venta": 35.00, "stock": 20},
        {"nombre": "Aceite 1L", "codigo": "AC001", "categoria": "Alimentos", "precio_costo": 15.00, "precio_venta": 22.00, "stock": 25},
        {"nombre": "Cloro 1L", "codigo": "CL001", "categoria": "Limpieza", "precio_costo": 2.50, "precio_venta": 4.50, "stock": 60},
    ]
    
    creados = 0
    for prod_data in productos_data:
        categoria = Category.objects.get(name=prod_data["categoria"])
        
        # Crear en catálogo
        producto_cat, created = Product.objects.get_or_create(
            codigo=prod_data["codigo"],
            defaults={
                "nombre": prod_data["nombre"],
                "categoria": categoria,
                "precio_costo": prod_data["precio_costo"],
                "precio_venta": prod_data["precio_venta"],
                "stock": prod_data["stock"],
                "activo": True
            }
        )
        if created:
            creados += 1
            print(f"➕ Producto creado en catálogo: {prod_data['nombre']}")
        
        # Crear en inventario
        producto_inv, created = Producto.objects.get_or_create(
            codigo=prod_data["codigo"],
            defaults={
                "codigo_barras": "",
                "nombre": prod_data["nombre"],
                "categoria": categoria,
                "precio_costo": prod_data["precio_costo"],
                "precio_venta": prod_data["precio_venta"],
                "stock": prod_data["stock"],
                "stock_minimo": 5,
                "activo": True
            }
        )
        if created:
            creados += 1
            print(f"➕ Producto creado en inventario: {prod_data['nombre']}")
    
    print(f"\n📊 Total productos creados: {creados}")
    print(f"📊 Total en inventario: {Producto.objects.count()}")

def menu():
    print("🔧 MENÚ DE RECUPERACIÓN DE PRODUCTOS")
    print("=" * 50)
    print("1. Importar desde catálogo (si hay datos en catalogo.models.Product)")
    print("2. Crear productos de ejemplo (si no hay datos)")
    print("3. Ver estado actual")
    print("4. Salir")
    
    opcion = input("\nSelecciona una opción (1-4): ")
    
    if opcion == "1":
        importar_desde_catalogo()
    elif opcion == "2":
        crear_productos_ejemplo()
    elif opcion == "3":
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"📁 Catálogo: {Product.objects.count()} productos")
        print(f"📦 Inventario: {Producto.objects.count()} productos")
        print(f"📁 Categorías: {Category.objects.count()} categorías")
    elif opcion == "4":
        print("👋 Saliendo...")
        return
    else:
        print("❌ Opción no válida")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    menu()
