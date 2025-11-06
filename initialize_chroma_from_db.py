"""
Initialize ChromaDB with Menu Items from PostgreSQL Database
"""

from vector_store.chroma_manager import ChromaDBManager
from database.db_manager import DatabaseManager
import json

def initialize_chroma_from_database():
    """Load menu items from PostgreSQL and index in ChromaDB"""
    
    print("\n" + "="*80)
    print("INITIALIZING CHROMADB FROM POSTGRESQL DATABASE")
    print("="*80)
    
    # Initialize managers
    db = DatabaseManager()
    chroma = ChromaDBManager()
    
    # Fetch all menu items from database
    print("\n[Database] Fetching menu items...")
    db_menu_items = db.get_all_menu_items()
    print(f"✓ Fetched {len(db_menu_items)} menu items from database")
    
    # Convert to ChromaDB format
    menu_items = []
    for item in db_menu_items:
        menu_items.append({
            'item_id': item['item_id'],
            'name': item['name'],
            'description': item['description'] or '',
            'restaurant_id': item['restaurant_id'],
            'restaurant_name': item['restaurant_name'],
            'price': float(item['price']),
            'cuisine_type': item['cuisine_type'],
            'tags': item['tags'] if isinstance(item['tags'], list) else json.loads(item['tags'] or '[]')
        })
    
    # Index in ChromaDB
    print("\n[ChromaDB] Indexing menu items...")
    chroma.index_menu_items(menu_items)
    
    # Print stats
    stats = chroma.get_collection_stats()
    db_stats = db.get_database_stats()
    
    print("\n" + "="*80)
    print("✓ INITIALIZATION COMPLETE")
    print("="*80)
    
    print(f"\nPostgreSQL Database:")
    for table, count in db_stats.items():
        print(f"  - {table}: {count} records")
    
    print(f"\nChromaDB Collections:")
    for name, count in stats.items():
        print(f"  - {name}: {count} documents")
    
    # Cleanup
    db.disconnect()
    
    print("\n")

if __name__ == "__main__":
    initialize_chroma_from_database()