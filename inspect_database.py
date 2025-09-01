#!/usr/bin/env python3
"""
Database Inspection Script
Shows the structure and contents of the FaceCheck database
"""

import sqlite3
import os
from datetime import datetime

def inspect_database():
    """Inspect the database structure and contents"""
    
    db_path = "instance/facerecognition.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    print("🔍 FaceCheck Database Inspection")
    print("=" * 50)
    print(f"📁 Database: {db_path}")
    print(f"📅 Last Modified: {datetime.fromtimestamp(os.path.getmtime(db_path))}")
    print("=" * 50)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    print(f"\n📊 Found {len(tables)} tables:")
    for table in tables:
        print(f"   • {table[0]}")
    
    print("\n" + "=" * 50)
    
    # Inspect each table
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        print("-" * 30)
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print("📝 Structure:")
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_str = " (PK)" if pk else ""
            not_null_str = " NOT NULL" if not_null else ""
            default_str = f" DEFAULT {default_val}" if default_val else ""
            print(f"   • {col_name}: {col_type}{not_null_str}{default_str}{pk_str}")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"\n📈 Row Count: {row_count}")
        
        # Show sample data (first 5 rows)
        if row_count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            rows = cursor.fetchall()
            
            print("📄 Sample Data:")
            col_names = [col[1] for col in columns]
            print(f"   Headers: {' | '.join(col_names)}")
            print("   " + "-" * (len(' | '.join(col_names)) + 5))
            
            for i, row in enumerate(rows, 1):
                row_str = ' | '.join(str(val) if val is not None else 'NULL' for val in row)
                print(f"   Row {i}: {row_str}")
            
            if row_count > 5:
                print(f"   ... and {row_count - 5} more rows")
        
        print()
    
    # Show relationships
    print("🔗 Foreign Key Relationships:")
    print("-" * 30)
    
    relationships_found = False
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = cursor.fetchall()
        
        for fk in foreign_keys:
            fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            print(f"   • {table_name}.{from_col} → {ref_table}.{to_col}")
            relationships_found = True
    
    if not relationships_found:
        print("   No foreign key relationships found")
    
    # Database size
    file_size = os.path.getsize(db_path)
    print(f"\n💾 Database Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ Database inspection completed!")

def show_table_details(table_name):
    """Show detailed information about a specific table"""
    
    db_path = "instance/facerecognition.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        print(f"❌ Table '{table_name}' not found!")
        conn.close()
        return
    
    print(f"\n🔍 Detailed View: {table_name}")
    print("=" * 50)
    
    # Get column info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    
    # Get all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    print(f"📊 Total Rows: {len(rows)}")
    print(f"📝 Columns: {', '.join(col_names)}")
    print("\n📄 All Data:")
    print("-" * 80)
    
    if rows:
        # Print header
        header = " | ".join(f"{col:15}" for col in col_names)
        print(header)
        print("-" * len(header))
        
        # Print data
        for row in rows:
            row_str = " | ".join(f"{str(val):15}" if val is not None else f"{'NULL':15}" for val in row)
            print(row_str)
    else:
        print("No data found in table")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Show specific table
        table_name = sys.argv[1]
        show_table_details(table_name)
    else:
        # Show all tables
        inspect_database()
        
        print("\n💡 To view a specific table in detail, run:")
        print("   python inspect_database.py <table_name>")
        print("\n   Examples:")
        print("   python inspect_database.py user")
        print("   python inspect_database.py student")
        print("   python inspect_database.py faculty")
        print("   python inspect_database.py course")
        print("   python inspect_database.py department")
