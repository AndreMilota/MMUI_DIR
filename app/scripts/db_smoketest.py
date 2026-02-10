import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools.sql import get_db_connection

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT,
            size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if sample data already exists
    cursor.execute('SELECT COUNT(*) FROM files')
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Seed with sample data only if empty
        sample_files = [
            ('Sample1.mp3', '/path/to/Sample1.mp3', 1024),
            ('Sample2.mp3', '/path/to/Sample2.mp3', 2048)
        ]
        
        cursor.executemany('INSERT INTO files (name, path, size) VALUES (?, ?, ?)', sample_files)
        print("Database created and seeded successfully.")
    else:
        print("Database already exists with data.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
