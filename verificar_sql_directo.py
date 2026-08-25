#!/usr/bin/env python
import os
import django
import sqlite3

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

def verificar_sql_directo():
    print("🔍 VERIFICACIÓN SQL DIRECTA")
    print("=" * 50)
    
    # Conectar directamente a SQLite
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Verificar todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"📊 Total tablas: {len(tables)}")
    
    # Buscar tablas con productos
    for table in tables:
        table_name = table[0]
        if 'producto' in table_name.lower() or 'product' in table_name.lower():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"📁 {table_name}: {count} registros")
            
            if count > 50:
                print(f"  🎯 ¡Tabla con muchos registros encontrada!")
                # Mostrar estructura
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                print(f"  📝 Columnas: {len(columns)}")
                for col in columns:
                    print(f"    - {col[1]} ({col[2]})")
                
                # Mostrar primeros 5 registros
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                print(f"  📋 Primeros 5 registros:")
                for i, row in enumerate(rows, 1):
                    print(f"    {i}. {row}")
    
    # Verificar si hay tablas con más de 100 registros
    print(f"\n🔍 Tablas con más de 100 registros:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        if count > 100:
            print(f"  📁 {table_name}: {count} registros")
    
    # Verificar específicamente las tablas que mencionaste
    print(f"\n🎯 Verificación específica:")
    try:
        cursor.execute("SELECT COUNT(*) FROM inventario_producto")
        count1 = cursor.fetchone()[0]
        print(f"📊 inventario_producto: {count1} registros")
        
        if count1 > 50:
            cursor.execute("SELECT nombre, stock, precio_venta FROM inventario_producto LIMIT 10")
            productos = cursor.fetchall()
            print(f"📋 Muestra de productos:")
            for i, (nombre, stock, precio) in enumerate(productos, 1):
                print(f"  {i}. {nombre[:40]} - Stock: {stock} - Precio: {precio}")
    except Exception as e:
        print(f"❌ Error al consultar inventario_producto: {e}")
    
    try:
        cursor.execute("SELECT COUNT(*) FROM catalogo_product")
        count2 = cursor.fetchone()[0]
        print(f"📊 catalogo_product: {count2} registros")
        
        if count2 > 50:
            cursor.execute("SELECT nombre, stock, precio_venta FROM catalogo_product LIMIT 10")
            productos = cursor.fetchall()
            print(f"📋 Muestra de productos:")
            for i, (nombre, stock, precio) in enumerate(productos, 1):
                print(f"  {i}. {nombre[:40]} - Stock: {stock} - Precio: {precio}")
    except Exception as e:
        print(f"❌ Error al consultar catalogo_product: {e}")
    
    conn.close()
    print("\n🎯 VERIFICACIÓN COMPLETADA")

if __name__ == "__main__":
    verificar_sql_directo()
