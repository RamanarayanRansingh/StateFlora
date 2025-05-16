from typing import Dict, Any
from contextlib import contextmanager
from langchain_core.tools import tool
from Data_Base.database import get_db
from Data_Base.models import Order, Product, Customer
from app.services.vectorService import vector_store

@tool
def place_order(customer_id: int, product_id: str, quantity: int) -> Dict[str, Any]:
    """
    Create a new order for a given product and quantity using SQLAlchemy.

    Args:
        customer_id (int): The ID of the customer placing the order.
        product_id (str): The ID of the product being ordered.
        quantity (int): The quantity of the product to order.

    Returns:
        Dict[str, Any]: Response containing order details or error message.
    """
    with contextmanager(get_db)() as db:
        # Check if product exists and has enough stock
        product = db.query(Product).filter(Product.product_id == product_id).first()
        
        if not product:
            return {
                "status": "error",
                "message": f"Product {product_id} not found"
            }
            
        if product.quantity < quantity:
            return {
                "status": "error",
                "message": f"Insufficient stock. Available: {product.quantity}"
            }
            
        # Create order
        new_order = Order(
            customer_id=customer_id,
            product_id=product_id,
            quantity=quantity,
            status="Processing"
        )
        db.add(new_order)
        
        # Update product stock
        product.quantity -= quantity
        db.flush()  # Flush to get the order_id
        
        return {
            "status": "success",
            "message": "Order placed successfully",
            "order_id": new_order.order_id,
            "total_amount": product.price * quantity,
            "product_name": product.name
        }

@tool
def cancel_order(customer_id: int, order_id: int) -> Dict[str, Any]:
    """
    Cancels an existing order and restores the product quantity using SQLAlchemy.
    
    Args:
        customer_id (int): The ID of the customer requesting cancellation.
        order_id (int): The ID of the order to cancel.

    Returns:
        Dict[str, Any]: Response containing confirmation or error message.
    """
    with contextmanager(get_db)() as db:
        # Check if order exists
        order = db.query(Order).filter(Order.order_id == order_id).first()
        
        if not order:
            return {
                "status": "error",
                "message": f"Order {order_id} not found"
            }

        # Ensure the order belongs to the requesting customer
        if order.customer_id != customer_id:
            return {
                "status": "error",
                "message": "You are not authorized to cancel this order"
            }
            
        if order.status == 'Cancelled':
            return {
                "status": "error",
                "message": "Order is already cancelled"
            }

        # Restore stock
        product = db.query(Product).filter(Product.product_id == order.product_id).first()
        if product:
            product.quantity += order.quantity
        
        # Update order status
        order.status = 'Cancelled'
        
        return {
            "status": "success",
            "message": f"Order {order_id} cancelled successfully"
        }

@tool
def check_order_status(order_id: int) -> Dict[str, Any]:
    """
    Checks the status of an existing order using SQLAlchemy.

    Args:
        order_id (int): The ID of the order.
    
    Returns:
        Dict[str, Any]: Response containing order details or error message.
    """
    with contextmanager(get_db)() as db:
        order = (
            db.query(Order, Product, Customer)
            .join(Product, Order.product_id == Product.product_id)
            .join(Customer, Order.customer_id == Customer.customer_id)
            .filter(Order.order_id == order_id)
            .first()
        )
        
        if not order:
            return {
                "status": "error",
                "message": f"Order {order_id} not found"
            }
            
        order_obj, product, customer = order
        
        return {
            "status": "success",
            "order_id": order_id,
            "customer_id": customer.customer_id,
            "customer_name": customer.name,
            "product_id": product.product_id,
            "product_name": product.name,
            "quantity": order_obj.quantity,
            "order_status": order_obj.status,
            "total_amount": product.price * order_obj.quantity
        }

@tool
def list_orders(customer_id: int) -> Dict[str, Any]:
    """
    List all orders placed by a specific customer using SQLAlchemy.

    Args:
        customer_id (int): The ID of the customer.

    Returns:
        Dict[str, Any]: Response containing list of orders or error message.
    """
    with contextmanager(get_db)() as db:
        orders = (
            db.query(Order, Product, Customer)
            .join(Product, Order.product_id == Product.product_id)
            .join(Customer, Order.customer_id == Customer.customer_id)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_id.desc())
            .all()
        )
        
        if not orders:
            return {
                "status": "success",
                "message": "No orders found",
                "orders": []
            }
            
        customer = orders[0].Customer
        
        order_list = [{
            "order_id": order.Order.order_id,
            "product_name": order.Product.name,
            "quantity": order.Order.quantity,
            "status": order.Order.status,
            "total_amount": order.Product.price * order.Order.quantity
        } for order in orders]
            
        return {
            "status": "success",
            "customer_id": customer_id,
            "customer_name": customer.name,
            "orders": order_list
        }

@tool
def get_product_recommendations(query: str, n_results: int = 3) -> Dict[str, Any]:
    """
    Get product recommendations based on a query, checking current availability in SQLite.

    Args:
        query (str): Search query for products
        n_results (int): Number of recommendations to return

    Returns:
        Dict[str, Any]: List of available recommended products
    """
    # Get semantic search results from vector store
    with contextmanager(get_db)() as db:
        # Update embeddings to ensure they're in sync with the database
        vector_store.update_product_embeddings(db)
        
        results = vector_store.query_products(
            query_text=query,
            n_results=n_results * 2  # Get extra results to account for filtering
        )

        # Check current availability in SQLite
        available_products = []
        seen_products = set()

        if results['ids'] and results['ids'][0]:
            for idx, product_id in enumerate(results['ids'][0]):
                # Skip if we've already seen this product
                if product_id in seen_products:
                    continue
                seen_products.add(product_id)

                # Get current product data from SQLite
                product = db.query(Product).filter(Product.product_id == product_id).first()

                # Only include if product exists and is in stock
                if product and product.quantity > 0:
                    # metadata = results['metadatas'][0][idx] if idx < len(results['metadatas'][0]) else {}
                    
                    available_products.append({
                        "product_id": product.product_id,
                        "name": product.name,
                        "description": product.description,
                        "price": product.price,
                        "quantity": product.quantity,
                        "type": product.type,
                        "relevance_score": results['distances'][0][idx] if idx < len(results['distances'][0]) else 1.0
                    })

                    if len(available_products) >= n_results:
                        break

        return {
            "status": "success",
            "recommendations": available_products[:n_results]
        }

@tool
def query_faqs(query: str, n_results: int = 3) -> Dict[str, Any]:
    """
    Search FAQs based on a query using vector similarity.

    Args:
        query (str): Question or search query
        n_results (int): Number of FAQ results to return

    Returns:
        Dict[str, Any]: Matching FAQ pairs
    """
    results = vector_store.query_faqs(
        query_text=query,
        n_results=n_results * 2  # Get extra to account for Q&A pairs
    )
    
    faqs = []
    seen_pairs = set()
    
    if results['metadatas'] and results['metadatas'][0]:
        for metadata in results['metadatas'][0]:
            if not metadata:
                continue
                
            # Create unique key for Q&A pair
            qa_key = f"{metadata['question']}:{metadata['answer']}"
            
            if qa_key not in seen_pairs:
                faqs.append({
                    "question": metadata['question'],
                    "answer": metadata['answer']
                })
                seen_pairs.add(qa_key)
                
                if len(faqs) >= n_results:
                    break

    return {
        "status": "success",
        "faqs": faqs[:n_results]
    }

@tool
def update_product_in_db(product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a product in the database and synchronize the vector store.
    
    Args:
        product_id (str): ID of the product to update
        updates (Dict[str, Any]): Fields to update and their new values
        
    Returns:
        Dict[str, Any]: Status and updated product information
    """
    with contextmanager(get_db)() as db:
        # Find the product
        product = db.query(Product).filter(Product.product_id == product_id).first()
        
        if not product:
            return {
                "status": "error",
                "message": f"Product with ID {product_id} not found"
            }
        
        # Update the product
        for field, value in updates.items():
            if hasattr(product, field):
                setattr(product, field, value)
        
        db.commit()
        
        # Update the vector store if the description was updated
        if 'description' in updates:
            vector_store.update_product_embeddings(db, force_full_sync=False)
        
        return {
            "status": "success",
            "message": f"Product {product_id} updated successfully",
            "product": {
                "product_id": product.product_id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "quantity": product.quantity,
                "type": product.type
            }
        }