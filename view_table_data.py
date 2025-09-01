#!/usr/bin/env python3
"""
Script to view all data in a specific table
"""

import sqlite3
import os
from tabulate import tabulate

def get_database_path():
    """Get the database path"""
    if os.path.exists("instance/facerecognition.db"):
        return "instance/facerecognition.db"
    elif os.path.exists("facerecognition.db"):
        return "facerecognition.db"
    else:
        raise FileNotFoundError("Database file not found.")

def view_table_data(table_name):
    """View all data in a specific table"""
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # Get all data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        print(f"📊 Table: {table_name}")
        print(f"📈 Total rows: {len(rows)}")
        print("=" * 80)
        
        if rows:
            # Display data in a nice table format
            print(tabulate(rows, headers=column_names, tablefmt="grid"))
        else:
            print("❌ No data found in this table.")
            
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def list_all_tables():
    """List all tables in the database"""
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print("📋 Available tables:")
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table[0]}")
        
        conn.close()
        return [table[0] for table in tables]
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return []

def main():
    """Main function"""
    print("🔍 FaceCheck Database Table Viewer")
    print("=" * 50)
    
    try:
        # List all tables
        tables = list_all_tables()
        
        if not tables:
            print("❌ No tables found.")
            return
        
        print("\nEnter table name or number:")
        user_input = input("➤ ").strip()
        
        # Handle numeric input
        if user_input.isdigit():
            table_index = int(user_input) - 1
            if 0 <= table_index < len(tables):
                table_name = tables[table_index]
            else:
                print("❌ Invalid table number.")
                return
        else:
            table_name = user_input
        
        # Check if table exists
        if table_name not in tables:
            print(f"❌ Table '{table_name}' not found.")
            return
        
        print()
        view_table_data(table_name)
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
