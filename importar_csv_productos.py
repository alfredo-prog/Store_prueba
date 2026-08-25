#!/usr/bin/env python
import os
import django
import csv
import pandas as pd

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

from inventario.models import Producto
from catalogo.models import Category, Product
from proveedores.models import Proveedor

def importar_desde_csv(ruta_archivo):
    """Importar productos desde un archivo CSV"""
    print(f"📁 Importando desde: {ruta_archivo}")
    print("=" * 50)
    
    try:
        # Intentar leer con pandas primero
        df = pd.read_csv(ruta_archivo)
        print(f"📊 Archivo CSV encontrado con {len(df)} filas")
        print(f"📝 Columnas: {list(df.columns)}")
        
        importados = 0
        errores = 0
        
        for index, row in df.iterrows():
            try:
                # Mapear columnas comunes
                nombre = row.get('nombre') or row.get('name') or row.get('Producto') or row.get('producto')
                codigo = row.get('codigo') or row.get('sku') or row.get('código') or f"PROD-{index+1:04d}"
                precio_costo = float(row.get('precio_costo') or row.get('costo') or row.get('precio_costo') or 0)
                precio_venta = float(row.get('precio_venta') or row.get('venta') or row.get('precio_venta') or precio_costo * 1.5)
                stock = int(row.get('stock') or row.get('cantidad') or row.get('existencia') or 0)
                categoria_nombre = row.get('categoria') or row.get('categoría') or 'Sin categoría'
                
                if not nombre:
                    print(f"⚠️ Fila {index+1}: Sin nombre, omitiendo")
                    errores += 1
                    continue
                
                # Crear o obtener categoría
                categoria, _ = Category.objects.get_or_create(
                    name=categoria_nombre,
                    defaults={'description': f'Categoría {categoria_nombre}'}
                )
                
                # Crear producto en catálogo
                producto_cat, created = Product.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'precio_costo': precio_costo,
                        'precio_venta': precio_venta,
                        'stock': stock,
                        'activo': True
                    }
                )
                
                # Crear producto en inventario
                producto_inv, created = Producto.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'precio_costo': precio_costo,
                        'precio_venta': precio_venta,
                        'stock': stock,
                        'activo': True
                    }
                )
                
                if created:
                    importados += 1
                    print(f"✅ Importado: {nombre[:30]}")
                else:
                    # Actualizar si ya existe
                    producto_inv.nombre = nombre
                    producto_inv.categoria = categoria
                    producto_inv.precio_costo = precio_costo
                    producto_inv.precio_venta = precio_venta
                    producto_inv.stock = stock
                    producto_inv.save()
                    print(f"🔄 Actualizado: {nombre[:30]}")
                    
            except Exception as e:
                print(f"❌ Error en fila {index+1}: {e}")
                errores += 1
        
        print(f"\n📊 RESUMEN:")
        print(f"✅ Importados: {importados}")
        print(f"🔄 Actualizados: {len(df) - errores - importados}")
        print(f"❌ Errores: {errores}")
        print(f"📊 Total en inventario: {Producto.objects.count()}")
        
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")

def importar_desde_excel(ruta_archivo):
    """Importar productos desde un archivo Excel"""
    print(f"📁 Importando desde Excel: {ruta_archivo}")
    print("=" * 50)
    
    try:
        df = pd.read_excel(ruta_archivo)
        print(f"📊 Archivo Excel encontrado con {len(df)} filas")
        print(f"📝 Columnas: {list(df.columns)}")
        
        # Procesar igual que CSV
        return importar_desde_dataframe(df)
        
    except Exception as e:
        print(f"❌ Error al leer Excel: {e}")

def importar_desde_dataframe(df):
    """Importar productos desde un DataFrame de pandas"""
    importados = 0
    errores = 0
    
    for index, row in df.iterrows():
        try:
            # Mapear columnas comunes
            nombre = row.get('nombre') or row.get('name') or row.get('Producto') or row.get('producto')
            codigo = row.get('codigo') or row.get('sku') or row.get('código') or f"PROD-{index+1:04d}"
            precio_costo = float(row.get('precio_costo') or row.get('costo') or row.get('precio_costo') or 0)
            precio_venta = float(row.get('precio_venta') or row.get('venta') or row.get('precio_venta') or precio_costo * 1.5)
            stock = int(row.get('stock') or row.get('cantidad') or row.get('existencia') or 0)
            categoria_nombre = row.get('categoria') or row.get('categoría') or 'Sin categoría'
            
            if not nombre:
                print(f"⚠️ Fila {index+1}: Sin nombre, omitiendo")
                errores += 1
                continue
            
            # Crear o obtener categoría
            categoria, _ = Category.objects.get_or_create(
                name=categoria_nombre,
                defaults={'description': f'Categoría {categoria_nombre}'}
            )
            
            # Crear producto en inventario
            producto_inv, created = Producto.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'categoria': categoria,
                    'precio_costo': precio_costo,
                    'precio_venta': precio_venta,
                    'stock': stock,
                    'activo': True
                }
            )
            
            if created:
                importados += 1
                print(f"✅ Importado: {nombre[:30]}")
            else:
                # Actualizar si ya existe
                producto_inv.nombre = nombre
                producto_inv.categoria = categoria
                producto_inv.precio_costo = precio_costo
                producto_inv.precio_venta = precio_venta
                producto_inv.stock = stock
                producto_inv.save()
                print(f"🔄 Actualizado: {nombre[:30]}")
                
        except Exception as e:
            print(f"❌ Error en fila {index+1}: {e}")
            errores += 1
    
    print(f"\n📊 RESUMEN:")
    print(f"✅ Importados: {importados}")
    print(f"🔄 Actualizados: {len(df) - errores - importados}")
    print(f"❌ Errores: {errores}")
    print(f"📊 Total en inventario: {Producto.objects.count()}")

def crear_template_csv():
    """Crear un template CSV para importar productos"""
    print("📝 Creando template CSV para importación")
    print("=" * 50)
    
    template_data = [
        ['nombre', 'codigo', 'categoria', 'precio_costo', 'precio_venta', 'stock'],
        ['Coca Cola 2L', 'CC001', 'Bebidas', '8.50', '12.00', '50'],
        ['Pepsi 2L', 'PP001', 'Bebidas', '7.50', '11.00', '45'],
        ['Papas Lays', 'PL001', 'Snacks', '3.00', '5.50', '100'],
        ['Arroz 5kg', 'AR001', 'Alimentos', '25.00', '35.00', '20'],
    ]
    
    with open('template_productos.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(template_data)
    
    print("✅ Template creado: template_productos.csv")
    print("📋 Columnas requeridas:")
    print("  - nombre: Nombre del producto")
    print("  - codigo: Código único (SKU)")
    print("  - categoria: Categoría del producto")
    print("  - precio_costo: Precio de compra")
    print("  - precio_venta: Precio de venta")
    print("  - stock: Cantidad en stock")

def menu():
    print("🔧 IMPORTADOR DE PRODUCTOS")
    print("=" * 50)
    print("1. Importar desde archivo CSV")
    print("2. Importar desde archivo Excel")
    print("3. Crear template CSV")
    print("4. Ver estado actual")
    print("5. Salir")
    
    opcion = input("\nSelecciona una opción (1-5): ")
    
    if opcion == "1":
        ruta = input("Ruta del archivo CSV: ")
        if os.path.exists(ruta):
            importar_desde_csv(ruta)
        else:
            print("❌ Archivo no encontrado")
    elif opcion == "2":
        ruta = input("Ruta del archivo Excel: ")
        if os.path.exists(ruta):
            importar_desde_excel(ruta)
        else:
            print("❌ Archivo no encontrado")
    elif opcion == "3":
        crear_template_csv()
    elif opcion == "4":
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"📦 Inventario: {Producto.objects.count()} productos")
        print(f"📁 Catálogo: {Product.objects.count()} productos")
        print(f"📁 Categorías: {Category.objects.count()} categorías")
    elif opcion == "5":
        print("👋 Saliendo...")
        return
    else:
        print("❌ Opción no válida")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    menu()
