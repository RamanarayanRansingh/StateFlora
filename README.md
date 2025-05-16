# StatefulFlora

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A LangGraph Architecture for Secure Conversational Commerce with Persistent Context and Human-in-the-Loop Verification

StatefulFlora is an innovative conversational AI agent for floral retail that addresses critical challenges in e-commerce automation through a stateful architecture built on LangGraph.

![System Architecture Overview](images/fig_1)

## 🌟 Key Features

- **Persistent Context Management** - Maintains dialogue and transaction state across multiple sessions using SQLite persistence
- **Secure Transaction Handling** - Balances automation with appropriate safeguards via hybrid tool routing system
- **Inventory-Aware Recommendations** - Synchronizes semantic product recommendations with rapidly changing inventory
- **Human-in-the-Loop Security** - Implements verification workflows for sensitive operations

## 🏗️ System Architecture

StatefulFlora's architecture consists of three main components:

1. **LangGraph State Machine**: A cyclic state graph that manages conversation flow, tool routing, and conversation history persistence
2. **SQLite Database**: Stores customer information, product inventory, order history, and conversation checkpoints
3. **ChromaDB Vector Store**: Enables semantic search for product recommendations and FAQ retrieval based on natural language queries

![LangGraph State Machine](assets/langgraph_state_machine.png)

## 💡 Core Innovations

### 1. Cyclic State Machine with SQLite Persistence

The system implements a stateful architecture combining LangGraph's cyclic state machine with SQLite persistence to maintain conversation and transaction history across sessions, ensuring seamless continuation of customer interactions.

### 2. Hybrid Tool Routing with Human Verification

Tools are categorized into "safe" operations that can proceed automatically and "sensitive" operations requiring human verification:

- **Safe Tools**: Operations that read but don't modify critical state (check_order_status, list_orders, query_faqs, get_product_recommendations)
- **Sensitive Tools**: Operations that modify critical state (place_order, cancel_order)

![Human Verification Workflow](assets/human_verification.png)

### 3. Real-Time Vector Database Synchronization

The system implements a robust vector synchronization system using ChromaDB with SentenceTransformer embeddings, ensuring recommendations reflect current inventory and preventing out-of-stock suggestions.

![Inventory-Aware Recommendations](assets/inventory_recommendations.png)

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- LangGraph
- SQLite
- ChromaDB
- SentenceTransformers
- Gemini 2.0 Flash API access

### Installation

```bash
# Clone the repository
git clone https://github.com/RamanarayanRansingh/StateFlora.git
cd StatefulFlora

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Basic Usage

```python
from statefulflora import StatefulFloraAgent

# Initialize the agent
agent = StatefulFloraAgent(
    db_path="statefulflora.db",
    vector_db_path="./vector_store"
)

# Start a conversation
response = agent.chat("I'm looking for a bouquet for my mother's birthday")
print(response)

# Continue conversation in a new session with context preserved
response = agent.chat("What were those flowers we were discussing yesterday?")
print(response)
```

## 📝 Example Use Cases

The system excels in the following scenarios:

### 1. Context Retention Across Sessions

![Context Retention Across Sessions](assets/context_retention.png)

The system maintains context (preferences, occasion, delivery timing) across multiple sessions through SQLite persistence, creating a seamless continuation of the shopping journey.

### 2. Human Verification for Sensitive Operations

![Human Verification for Order Placement](assets/place_order_verification.png)
![Human Verification for Order Cancellation](assets/cancel_order_verification.png)

The hybrid tool routing system identifies sensitive operations (order placement, cancellation) and routes them for human verification before processing.

### 3. Inventory-Aware Recommendations

![Inventory-Aware Recommendations](assets/inventory_recommendations.png)

The real-time vector database synchronization prevents recommending out-of-stock items and enables semantic understanding of natural language queries like "similar arrangement."

## 📊 Performance

StatefulFlora demonstrates significant advantages in context maintenance and security controls compared to other automated solutions, while maintaining good user experience.

| Feature | Performance Assessment | Key Observations |
|---------|------------------------|------------------|
| Context Retention | Strong | System successfully maintains user preferences and order details across multiple sessions |
| Transaction Security | Very Strong | Human verification prevents unauthorized operations while permission-based tool routing allows automation of safe actions |
| Natural Language Understanding | Moderate to Strong | System handles most conversational queries appropriately |
| Inventory Integration | Strong | Real-time vector synchronization prevents recommendations of out-of-stock items |
| Response Time | Moderate | Additional security and state persistence layers add slight latency but remain within acceptable thresholds |

## 🔍 Implementation Considerations

Organizations considering the adoption of this approach should consider several practical factors:

1. **Domain-Specific Knowledge Requirements**: Implementing the tool classification system requires domain expertise to properly categorize operations based on risk levels
2. **Integration Complexity**: The SQLite persistence layer requires integration with existing e-commerce databases and inventory management systems
3. **Human Resource Planning**: Staff must be trained to handle verification requests efficiently, particularly during peak periods

## 🧩 Architectural Variations

Several architectural variations can address different deployment scenarios:

1. **Lightweight Implementation**: For smaller retailers, the system can be simplified by using in-memory databases with periodic backups instead of full SQLite persistence
2. **Enterprise Scale**: For large retailers, the SQLite database can be replaced with distributed databases like PostgreSQL or MongoDB for improved concurrency
3. **Multi-Modal Extension**: The framework can be extended to support image-based product search by integrating multi-modal embedding models

## 📚 Citation

If you use StatefulFlora in your research, please cite our paper:

```bibtex
@article{ransingh2025statefulflora,
  title={StatefulFlora: A LangGraph Architecture for Secure Conversational Commerce with Persistent Context and Human-in-the-Loop Verification},
  author={Ransingh, Ramanarayan and Agrawal, Arun},
  journal={},
  year={2025}
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👏 Acknowledgments

- The authors thank the reviewers for their valuable feedback and the retail partners who participated in the case study evaluation.
