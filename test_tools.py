from app.services.tools import (
    place_order, cancel_order, check_order_status, 
    list_orders, get_product_recommendations, query_faqs, update_product_in_db
)

def test_tools():
    # Test placing an order
    order_result = place_order.invoke({
        'customer_id': 2, 
        'product_id': 'P009', 
        'quantity': 3
    })
    print(f"Place Order Result: {order_result}")

    # Test canceling an order
    cancel_result = cancel_order.invoke({
        'order_id': 3,
        'customer_id': 5,
    })
    print(f"Cancel Order Result: {cancel_result}")

    # Test checking order status
    status_result = check_order_status.invoke({
        'order_id': 1 
    })
    print(f"Check Order Status Result: {status_result}")

    # Test listing orders
    list_result = list_orders.invoke({
        'customer_id': 1
    })
    print(f"List Orders Result: {list_result}")

    # Test getting product recommendations
    recommendations_result = get_product_recommendations.invoke({
        'query': "flowers for birthday",
        'n_results': 3
    })
    print(f"Product Recommendations Result: {recommendations_result}")

    # Test querying FAQs
    faqs_result = query_faqs.invoke({
        'query': "What is the return policy?",
        'n_results': 2
    })
    print(f"FAQ Query Result: {faqs_result}")

    # Test updating a product in the database
    update_result = update_product_in_db.invoke({
        'product_id': 'P009',
        'updates': {
            'price': 19.99,
            'quantity': 10
        }
    })
    print(f"Update Product Result: {update_result}")

if __name__ == "__main__":
    test_tools()
