import sqlite3
import os

# Database Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'olist.sqlite')

def drop_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"🔌 Connected to: {DB_PATH}")
    
    # Check if table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cursor.fetchone():
        try:
            # The Danger Zone ⚠️
            cursor.execute(f"DROP TABLE {table_name}")
            conn.commit()
            print(f"🗑️  SUCCESS: Table '{table_name}' has been permanently deleted.")
        except Exception as e:
            print(f"❌ Error deleting table: {e}")
    else:
        print(f"⚠️  Table '{table_name}' does not exist.")
    
    conn.close()

if __name__ == "__main__":
    # Change this name to whatever table you want to delete
    target_table = "silver_marketing_campaigns"
    
    confirm = input(f"Are you sure you want to delete '{target_table}'? (y/n): ")
    if confirm.lower() == 'y':
        drop_table(target_table)
    else:
        print("Operation cancelled.")