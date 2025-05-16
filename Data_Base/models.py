from sqlalchemy import JSON, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from Data_Base.database import Base
from datetime import datetime

class Customer(Base):
    __tablename__="customers"

    customer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__="products"

    product_id = Column(String, primary_key=True,index=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)


class Order(Base):
    __tablename__="orders"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String,ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="Pending")
    
    customer = relationship("Customer",back_populates="orders")
    product = relationship("Product")


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    thread_id = Column(String, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    pending_approval = Column(JSON, nullable=True)
    
    customer = relationship("Customer")
