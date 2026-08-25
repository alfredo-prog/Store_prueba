#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

from django.db import connection

def verificar_tablas():
    print("🔍 VERIFICANDO TABLAS DE PRODUCTOS")
    print("=" * 50)
    
    cursor = connection.cursor()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    all_tables = [table[0] for table in cursor.fetchall()]
    
    print(f"📊 Total tablas en BD: {len(all_tables)}")
    
    # Buscar tablas relacionadas con productos
    producto_tables = [table for table in all_tables if 'producto' in table.lower() or 'product' in table.lower()]
    
    print(f"\n📋 Tablas relacionadas con productos:")
    for table in producto_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  📁 {table}: {count} registros")
        
        # Mostrar primeros registros si hay muchos
        if count > 10:
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            sample = cursor.fetchall()
            print(f"    📝 Muestra: {len(sample)} registros")
    
    # Verificar tabla específica inventario_producto
    if 'inventario_producto' in all_tables:
        cursor.execute("SELECT COUNT(*) FROM inventario_producto")
        count = cursor.fetchone()[0]
        print(f"\n📊 Tabla actual (inventario_producto): {count} registros")
        
        if count > 0:
            cursor.execute("SELECT nombre, stock, activo FROM inventario_producto LIMIT 5")
            productos = cursor.fetchall()
            print("📝 Muestra de productos:")
            for i, (nombre, stock, activo) in enumerate(productos, 1):
                estado = "✅ Activo" if activo else "❌ Inactivo"
                print(f"  {i}. {nombre[:30]} - Stock: {stock} - {estado}")
    
    # Buscar tabla con muchos registros
    print(f"\n🔍 Buscando tabla con más de 50 registros:")
    for table in all_tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count > 50:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"  📁 {table}: {count} registros")
            print(f"    📝 Columnas: {len(columns)}")
            # Mostrar estructura básica
            for col in columns[:5]:  # Primeras 5 columnas
                print(f"      - {col[1]} ({col[2]})")
    
    print("\n🎯 VERIFICACIÓN COMPLETADA")

if __name__ == "__main__":
    verificar_tablas()
