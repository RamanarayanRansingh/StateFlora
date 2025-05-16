import json
import sqlite3
import os

with open("create_db/inventory.json","r",encoding="utf-8") as f:
    products = json.load(f)

db_path = os.path.abspath("Data_Base/db/flower_shop.db")


os.makedirs(os.path.dirname(db_path),exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# PRODUCT TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS products(
               product_id VARCHAR PRIMARY KEY,
               name TEXT,
               quantity INTEGER,
               price REAL,
               type TEXT,
               description TEXT
               )
""")

for product in products:
    cursor.execute("""
INSERT INTO products(product_id, name, quantity, price, type, description)
                   VALUES(?,?,?,?,?,?)
""",(product["id"], product["name"], product["quantity"], product["price"], product["type"], product["description"]))
    

# CUSTOMER TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS customers(
               customer_id INTEGER PRIMARY KEY,
               name TEXT,
               email TEXT)
""")

customers_data = [
    ("1","Ram","ram@gmail.com"),
    ("2","Ankit","ankit@gmail.com"),
    ("3","Rajnish","rajnish@gmail.com"),
    ("4","Bishal","bishal@gmail.com"),
    ("5","Dibas","dibas@gmail.com"),
]

cursor.executemany("""
INSERT INTO customers(customer_id,name,email)
                   VALUES (?,?,?)
""",customers_data)


# ORDER TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
               order_id INTEGER PRIMARY KEY,
               customer_id INTEGER,
               product_id TEXT,
               quantity INTEGER,
               status TEXT,
               FOREIGN KEY (customer_id) REFERENCES customers(customer_id))
""")

orders_data = [
    ("1","1","Processing","P001",1),
    ("2","3","Shipped","P023",3),
]

cursor.executemany("""
INSERT INTO orders(order_id,customer_id,status,product_id, quantity)
                   VALUES(?,?,?,?,?)
""",orders_data)

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation_history(
               thread_id TEXT PRIMARY KEY,
               customer_id INTEGER NOT NULL,
               messages TEXT NOT NULL,
               created_at TEXT DEFAULT CURRENT_TIMESTAMP,
               updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
               pending_approval TEXT,

               FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
""")

conn.commit()
conn.close()

print("success")
    
