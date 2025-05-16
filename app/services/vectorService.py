from chromadb import PersistentClient
from typing import List, Dict, Optional
from chromadb.api.types import EmbeddingFunction
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from contextlib import contextmanager
from datetime import datetime
import json

from Data_Base.database import get_db
from Data_Base.models import Product

class CustomEmbeddingClass(EmbeddingFunction):
    def __init__(self):
        # Initialize the SentenceTransformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

    def __call__(self, input: List[str]) -> List[List[float]]:
        # Encode the input texts and return as a list of lists
        return self.model.encode(input).tolist()

class VectorStore:
    def __init__(self, db_path: str = 'Data_Base/db/chroma_db'):
        self.db = PersistentClient(path=db_path)
        self.embedding_function = CustomEmbeddingClass()
        
        # Track last update time for products
        self.last_product_update = datetime.min

        # Create collections
        self.faq_collection = self.db.get_or_create_collection(
            name='FAQ',
            embedding_function=self.embedding_function
        )
        
        self.product_collection = self.db.get_or_create_collection(
            name='Products',
            embedding_function=self.embedding_function
        )

        # Initialize collections
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Initialize the collections if they're empty"""
        self._initialize_faq_collection()
        self._initialize_product_collection()
    
    def _initialize_faq_collection(self):
        """Initialize the FAQ collection from JSON (since FAQs are static)"""
        
        # Skip if collection is already populated
        if self.faq_collection.count() > 0:
            return
            
        try:
            with open('create_db/FAQ.json', 'r') as f:
                faqs = json.load(f)

            # Add both questions and answers for better matching
            documents = []
            ids = []
            metadatas = []

            for idx, faq in enumerate(faqs):
                # Add question
                documents.append(faq['question'])
                ids.append(f"q_{idx}")
                metadatas.append(faq)

                # Add answer
                documents.append(faq['answer'])
                ids.append(f"a_{idx}")
                metadatas.append(faq)

            self.faq_collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Error initializing FAQ collection: {e}")
    
    def _initialize_product_collection(self):
        """Initialize the product collection directly from SQLite database"""
        # Skip if collection is already populated and we'll do sync updates instead
        if self.product_collection.count() > 0:
            return
            
        try:
            with contextmanager(get_db)() as db:
                # Get all products from the database
                products = db.query(Product).all()
                
                if not products:
                    print("No products found in the database.")
                    return
                
                documents = []
                ids = []
                metadatas = []
                
                for product in products:
                    if not product.description:
                        continue  # Skip products without descriptions
                        
                    # Create the document (description) and metadata
                    documents.append(product.description)
                    ids.append(str(product.product_id))
                    
                    # Create metadata from the SQLAlchemy model
                    metadata = {
                        'product_id': product.product_id,
                        'name': product.name,
                        'price': float(product.price),
                        'type': product.type,
                        'description': product.description,
                        'last_updated': datetime.now().isoformat()
                    }
                    metadatas.append(metadata)
                
                if documents:
                    self.product_collection.add(
                        documents=documents,
                        ids=ids,
                        metadatas=metadatas
                    )
                
                self.last_product_update = datetime.now()
        except Exception as e:
            print(f"Error initializing product collection: {e}")
    
    def update_product_embeddings(self, db: Session, force_full_sync: bool = False):
        """
        Update product embeddings based on changes in the SQLite database
        
        Args:
            db: SQLAlchemy database session
            force_full_sync: Whether to force a full synchronization
        """
        try:
            # Check for any updates since last sync
            if force_full_sync:
                # Get all products and rebuild the collection
                products = db.query(Product).all()
                
                # First, get existing IDs
                existing_ids = []
                try:
                    existing_ids = [item for item in self.product_collection.get()['ids']]
                except:
                    # Collection might be empty
                    pass
                
                existing_ids_set = set(existing_ids)
                
                # Then, process updates and new items
                for product in products:
                    product_id = str(product.product_id)
                    
                    # Skip products without descriptions
                    if not product.description:
                        continue
                        
                    metadata = {
                        'product_id': product.product_id,
                        'name': product.name,
                        'price': float(product.price),
                        'type': product.type,
                        'description': product.description,
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    if product_id in existing_ids_set:
                        # Update existing item
                        self.product_collection.update(
                            ids=[product_id],
                            documents=[product.description],
                            metadatas=[metadata]
                        )
                    else:
                        # Add new item
                        self.product_collection.add(
                            ids=[product_id],
                            documents=[product.description],
                            metadatas=[metadata]
                        )
                    
                    # Remove ID from set to track what we've processed
                    if product_id in existing_ids_set:
                        existing_ids_set.remove(product_id)
                
                # Delete any products that no longer exist
                if existing_ids_set:
                    self.product_collection.delete(ids=list(existing_ids_set))
            
            else:
                # More efficient partial update logic
                
                # 1. Get current product IDs from vector store
                vector_products = set()
                try:
                    items = self.product_collection.get()
                    if items and 'ids' in items:
                        vector_products = set(items['ids'])
                except:
                    # Collection might be empty
                    pass
                
                # 2. Get current product IDs from database
                db_products = {str(p.product_id): p for p in db.query(Product).all()}
                db_product_ids = set(db_products.keys())
                
                # 3. Find products to add (in DB but not in vector store)
                products_to_add = db_product_ids - vector_products
                
                # 4. Find products to remove (in vector store but not in DB)
                products_to_remove = vector_products - db_product_ids
                
                # 5. Process additions
                if products_to_add:
                    add_ids = []
                    add_docs = []
                    add_metadatas = []
                    
                    for pid in products_to_add:
                        product = db_products[pid]
                        if not product.description:
                            continue
                            
                        add_ids.append(str(product.product_id))
                        add_docs.append(product.description)
                        add_metadatas.append({
                            'product_id': product.product_id,
                            'name': product.name,
                            'price': float(product.price),
                            'type': product.type,
                            'description': product.description,
                            'last_updated': datetime.now().isoformat()
                        })
                    
                    if add_ids:
                        self.product_collection.add(
                            ids=add_ids,
                            documents=add_docs,
                            metadatas=add_metadatas
                        )
                
                # 6. Process removals
                if products_to_remove:
                    self.product_collection.delete(ids=list(products_to_remove))
                
                # 7. Check for updates to existing products
                for pid in db_product_ids.intersection(vector_products):
                    product = db_products[pid]
                    if not product.description:
                        continue
                        
                    # Get the current metadata
                    current_metadata = None
                    try:
                        items = self.product_collection.get(ids=[pid])
                        if items and 'metadatas' in items and items['metadatas']:
                            current_metadata = items['metadatas'][0]
                    except:
                        pass
                    
                    # Check if any fields have changed
                    if current_metadata and (
                        current_metadata.get('name') != product.name or
                        current_metadata.get('price') != float(product.price) or
                        current_metadata.get('type') != product.type or
                        current_metadata.get('description') != product.description
                    ):
                        self.product_collection.update(
                            ids=[pid],
                            documents=[product.description],
                            metadatas=[{
                                'product_id': product.product_id,
                                'name': product.name,
                                'price': float(product.price),
                                'type': product.type,
                                'description': product.description,
                                'last_updated': datetime.now().isoformat()
                            }]
                        )
            
            self.last_product_update = datetime.now()
            
        except Exception as e:
            print(f"Error updating product embeddings: {e}")
            
    def query_products(self, query_text: str, n_results: int = 5, filter_condition: Optional[Dict] = None):
        """
        Query the product collection
        
        Args:
            query_text: The search query
            n_results: Number of results to return
            filter_condition: Optional filter to apply to results
            
        Returns:
            Dict containing query results
        """
        return self.product_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_condition
        )
        
    def query_faqs(self, query_text: str, n_results: int = 3):
        """
        Query the FAQ collection
        
        Args:
            query_text: The search query
            n_results: Number of results to return
            
        Returns:
            Dict containing query results
        """
        return self.faq_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

# Create singleton instance
vector_store = VectorStore()