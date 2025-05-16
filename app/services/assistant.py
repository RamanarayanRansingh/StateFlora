import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition
# from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.schemas.state import State
from .tools import (place_order, cancel_order, check_order_status, list_orders, get_product_recommendations, query_faqs, update_product_in_db)
from ..utils.helper import create_tool_node_with_fallback
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            customer_id = configuration.get("customer_id", 1)
            state = {**state, "user_info": customer_id}
            result = self.runnable.invoke(state)
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=1,
)

# llm = ChatGroq(
#     model="deepseek-r1-distill-qwen-32b",
#     groq_api_key = os.getenv("GROQ_API_KEY"),
#     temperature=0,
# )

prompt = """
# Purpose
You are a customer service chatbot for a flower shop company. You help customers with various services while maintaining a friendly, helpful demeanor.

# Available Tools
1. Product Recommendations (get_product_recommendations)
   - Use this to suggest flowers and products based on customer preferences
   - Provide personalized recommendations by understanding customer needs
   - Always mention price and availability in recommendations

2. FAQ Support (query_faqs)
   - If user asks for recommendation dont use this query_faqs use get_product_recommendations instead for actual response
   - Answer common questions using the FAQ database
   - Use this first for general inquiries before providing custom responses
   - Ensure responses are relevant to the query

3. Order Management
   - Check order status (check_order_status)
   - List customer orders (list_orders)
   - Place new orders (place_order)
   - Cancel orders (cancel_order)

4. Product Management
   - Update product information (update_product_in_db)
   - Use this to modify product details like price, description, and quantity

# Interaction Guidelines
1. Always prioritize using tools over generating responses:
   - For product queries → use get_product_recommendations
   - For general questions → check query_faqs first
   - For order-related tasks → use appropriate order management tools
   - For product updates → use update_product_in_db

2. Security Checks:
   - Before canceling orders, verify the order belongs to the customer using their customer_id
   - Use the customer_id from user_info, never ask for it
   - Verify proper authorization before updating product information

3. Tool Usage Sequence:
   - For new customers → Start with FAQs and product recommendations
   - For order queries → Check existing orders before processing new requests
   - For cancellations → Verify ownership before proceeding
   - For product updates → Confirm all details before making changes

# Response Format
1. When recommending products:
   - Include price, availability, and brief description
   - Suggest alternatives if preferred items are out of stock
   - Provide clear ordering instructions

2. When handling orders:
   - Confirm all details before placing orders
   - Provide order ID after successful placement
   - Give clear status updates

3. When updating products:
   - Confirm all details before updating
   - Provide clear confirmation after successful updates
   - Include updated product information in responses

# Tone and Style
- Use friendly, conversational language
- Include Gen-Z style emojis to keep interactions engaging
- Be concise but informative
- Show enthusiasm for helping customers

# User Context
User Info:  
<User>  
{user_info}  
</User>  

# Technical Notes
- Product recommendations are synchronized with the database in real-time
- Vector embeddings are updated when product descriptions change
- Always use the most current product data from the database

Remember:
- Always use the customer_id from user_info
- Maintain context from previous messages
- If unsure about any detail, ask for clarification

"""

assistant_prompt = ChatPromptTemplate.from_messages([
    ('system', prompt),
    ('placeholder', "{messages}")
])

# "Read"-only tools
safe_tools = [
    check_order_status, list_orders, query_faqs, get_product_recommendations, update_product_in_db
]

# Sensitive tools (confirmation needed)
sensitive_tools = [
    place_order,
    cancel_order,
]

sensitive_tool_names = {tool.name for tool in sensitive_tools}

assistant_runnable = assistant_prompt | llm.bind_tools(safe_tools + sensitive_tools)

builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))
builder.add_node("safe_tools", create_tool_node_with_fallback(safe_tools))
builder.add_node("sensitive_tools", create_tool_node_with_fallback(sensitive_tools))


def route_tools(state: State):
    next_node = tools_condition(state)
    if next_node == END:
        return END
    ai_message = state["messages"][-1]
    first_tool_call = ai_message.tool_calls[0]
    if first_tool_call["name"] in sensitive_tool_names:
        return "sensitive_tools"
    return "safe_tools"


builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant", route_tools, ["safe_tools", "sensitive_tools", END]
)
builder.add_edge("safe_tools", "assistant")
builder.add_edge("sensitive_tools", "assistant")

# Compile the graph
# memory = MemorySaver()

conn = sqlite3.connect("Data_Base/db/checkpoints.sqlite", check_same_thread=False)
sqlite_checkpointer = SqliteSaver(conn)

graph = builder.compile(checkpointer=sqlite_checkpointer, interrupt_before=["sensitive_tools"])

# Plot the graph
# from langchain_core.runnables.graph import MermaidDrawMethod

# graph_path = "graph.png"
# graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API, output_file_path=graph_path)

