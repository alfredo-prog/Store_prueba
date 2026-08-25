#!/usr/bin/env python
import os
import django
import mysql.connector
from mysql.connector import Error

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'store_prueba.settings')
django.setup()

def probar_conexion_mysql():
    print("🔍 PROBANDO CONEXIÓN MYSQL")
    print("=" * 50)
    
    # Configuración de conexión
    config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'database': 'store_prueba',
        'charset': 'utf8mb4'
    }
    
    try:
        # Intentar conexión
        connection = mysql.connector.connect(**config)
        
        if connection.is_connected():
            print("✅ Conexión exitosa a MySQL!")
            
            # Obtener información del servidor
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"📊 Versión MySQL: {version}")
            
            # Listar bases de datos
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print(f"📁 Bases de datos disponibles:")
            for db in databases:
                print(f"  - {db[0]}")
            
            # Verificar tablas en store_prueba
            cursor.execute("USE store_prueba")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"\n📋 Tablas en store_prueba:")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  📁 {table_name}: {count} registros")
                
                # Si es tabla de productos, mostrar muestra
                if 'producto' in table_name.lower() or 'product' in table_name.lower():
                    if count > 50:
                        print(f"    🎯 ¡Tabla con muchos registros!")
                        cursor.execute(f"SELECT nombre, stock, precio_venta FROM {table_name} LIMIT 5")
                        productos = cursor.fetchall()
                        print(f"    📋 Muestra de productos:")
                        for i, (nombre, stock, precio) in enumerate(productos, 1):
                            print(f"      {i}. {nombre[:40]} - Stock: {stock} - Precio: {precio}")
            
            cursor.close()
            connection.close()
            print("\n🎉 Prueba completada exitosamente!")
            
        else:
            print("❌ No se pudo conectar a MySQL")
            
    except Error as e:
        print(f"❌ Error de conexión: {e}")
        print("\n🔧 Soluciones posibles:")
        print("1. Verificar que MySQL esté instalado y corriendo")
        print("2. Verificar usuario y contraseña")
        print("3. Verificar nombre de la base de datos")
        print("4. Verificar host y puerto")

def probar_conexion_django():
    print("\n🔍 PROBANDO CONEXIÓN DJANGO A MYSQL")
    print("=" * 50)
    
    try:
        from django.db import connection
        cursor = connection.cursor()
        
        # Probar consulta simple
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✅ Conexión Django-MySQL exitosa: {result}")
        
        # Verificar tablas
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"📋 Tablas encontradas: {len(tables)}")
        
        # Buscar tablas de productos
        for table in tables:
            table_name = table[0]
            if 'producto' in table_name.lower() or 'product' in table_name.lower():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"📁 {table_name}: {count} registros")
        
    except Exception as e:
        print(f"❌ Error en conexión Django: {e}")

if __name__ == "__main__":
    probar_conexion_mysql()
    probar_conexion_django()
