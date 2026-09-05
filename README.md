# FinGraph

## Fraud Intelligence and Network Analysis System

FinGraph is a fraud detection and financial intelligence project that analyzes suspicious transactions and account relationships using graph-based analysis.

The system uses Neo4j to store and analyze connected financial data and provides an interactive dashboard for fraud investigation and risk analysis.

## Features

- Fraud transaction detection and analysis
- Fraud alerts and account search
- Account details and transaction history
- Fraud hub identification
- Graph-based risk account analysis
- Fraud network visualization
- Fraud pattern analysis
- Country-wise fraud analysis
- Fraud transaction type analysis
- Risk distribution and severity analysis

## Technologies Used

- Python
- FastAPI
- Neo4j
- Cypher Query Language
- JavaScript
- HTML
- CSS
- Chart.js
- vis-network

## Project Structure

```text
FINGRAPH/
├── api/
│   └── main.py
├── dashboard/
│   └── index.html
├── .env
└── README.md
```

## Setup and Installation

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install the required dependencies.
4. Configure Neo4j connection details in the `.env` file.
5. Start the FastAPI backend:

```bash
uvicorn api.main:app --reload --port 8000
```

6. Open `dashboard/index.html` using Live Server.

## API Configuration

Create a `.env` file in the project root:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

## Project Output

The FinGraph dashboard provides an interactive view of:

- Suspicious financial transactions
- Fraud patterns
- High-risk accounts
- Fraud hubs
- Transaction networks
- Risk analysis

This helps users investigate suspicious financial activity using graph-based relationships.

## Future Improvements

- Advanced machine learning-based fraud detection
- Real-time transaction monitoring
- Improved risk scoring
- Automated fraud alerts
- Additional graph analytics

## Author

FinGraph Project

## Testing and Verification

The FinGraph system was tested to verify the integration between the Neo4j database, FastAPI backend, and interactive dashboard.

### Tested Features

- Fraud Patterns API
- Risk Accounts API
- Fraud Hubs API
- Fraud Alerts
- Account Details
- Fraud Network
- Dashboard Charts
- Interactive Search
- Responsive Dashboard Layout

All major APIs and dashboard features were tested successfully.

## Project Status

The FinGraph Fraud Intelligence and Network Analysis System has been successfully developed and tested.