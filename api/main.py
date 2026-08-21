import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase


# ======================================
# Configuration
# ======================================

URI = "bolt://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = os.getenv("NEO4J_PASSWORD")


# ======================================
# FastAPI
# ======================================

app = FastAPI(
    title="FinGraph Fraud Detection API",
    description="Graph-Based Financial Fraud Intelligence API",
    version="1.0.0"
)


# ======================================
# CORS
# ======================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ======================================
# Neo4j Driver
# ======================================

driver = None

if PASSWORD:
    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD)
    )


# ======================================
# HOME
# ======================================

@app.get("/")
def home():

    return {
        "project": "FinGraph",
        "status": "running",
        "service": "Fraud Detection API"
    }


# ======================================
# STATISTICS
# ======================================

@app.get("/statistics")
def statistics():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (t:Transaction)

    RETURN
        count(t) AS total_transactions,

        count(
            CASE
                WHEN t.fraud_status = 'FRAUD'
                THEN 1
            END
        ) AS fraud_transactions,

        sum(
            CASE
                WHEN t.fraud_status = 'FRAUD'
                THEN t.amount
                ELSE 0
            END
        ) AS total_fraud_amount
    """

    with driver.session() as session:

        record = session.run(query).single()

        total = record["total_transactions"] or 0
        fraud = record["fraud_transactions"] or 0
        amount = record["total_fraud_amount"] or 0

        percentage = 0

        if total > 0:
            percentage = round(
                fraud * 100 / total,
                2
            )

        return {
            "total_transactions": total,
            "fraud_transactions": fraud,
            "fraud_percentage": percentage,
            "total_fraud_amount": round(
                float(amount),
                2
            )
        }


# ======================================
# FRAUD TRANSACTIONS
# ======================================

@app.get("/fraud")
def fraud_transactions():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WHERE t.fraud_status = 'FRAUD'

    RETURN
        t.id AS transaction_id,
        s.id AS sender,
        r.id AS receiver,
        t.amount AS amount,
        t.country AS country,
        t.fraud_pattern AS fraud_pattern

    ORDER BY t.amount DESC

    LIMIT 100
    """

    with driver.session() as session:

        result = session.run(query)

        data = []

        for record in result:

            data.append({
                "transaction_id": record["transaction_id"],
                "sender": record["sender"],
                "receiver": record["receiver"],
                "amount": round(
                    float(record["amount"] or 0),
                    2
                ),
                "country": record["country"],
                "fraud_pattern": record["fraud_pattern"]
            })

        return {
            "count": len(data),
            "transactions": data
        }


# ======================================
# FRAUD HUBS
# ======================================

@app.get("/fraud-hubs")
def fraud_hubs():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WHERE t.fraud_status = 'FRAUD'

    WITH
        r,
        count(DISTINCT s) AS unique_senders,
        count(t) AS fraud_transactions,
        sum(t.amount) AS total_fraud_amount

    RETURN
        r.id AS fraud_hub,
        unique_senders,
        fraud_transactions,
        total_fraud_amount

    ORDER BY total_fraud_amount DESC

    LIMIT 20
    """

    with driver.session() as session:

        result = session.run(query)

        data = []

        for record in result:

            data.append({
                "fraud_hub": record["fraud_hub"],
                "unique_senders": record["unique_senders"],
                "fraud_transactions": record["fraud_transactions"],
                "total_fraud_amount": round(
                    float(record["total_fraud_amount"] or 0),
                    2
                )
            })

        return data


# ======================================
# RISK ACCOUNTS
# ======================================

@app.get("/risk-accounts")
def risk_accounts():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WHERE t.fraud_status = 'FRAUD'

    WITH
        s,
        collect(DISTINCT r.id) AS receivers,
        count(t) AS fraud_transactions,
        sum(t.amount) AS total_fraud_amount

    WITH
        s,
        receivers,
        fraud_transactions,
        total_fraud_amount,

        (
            fraud_transactions * 10 +
            size(receivers) * 15 +
            total_fraud_amount / 1000
        ) AS risk_score

    RETURN
        s.id AS account,
        size(receivers) AS connected_receivers,
        fraud_transactions,
        total_fraud_amount,
        risk_score,

        CASE
            WHEN risk_score >= 40 THEN 'CRITICAL'
            WHEN risk_score >= 30 THEN 'HIGH'
            WHEN risk_score >= 20 THEN 'MEDIUM'
            ELSE 'LOW'
        END AS risk_category

    ORDER BY risk_score DESC

    LIMIT 20
    """

    with driver.session() as session:

        result = session.run(query)

        data = []

        for record in result:

            data.append({
                "account": record["account"],
                "connected_receivers":
                    record["connected_receivers"],
                "fraud_transactions":
                    record["fraud_transactions"],
                "total_fraud_amount":
                    round(
                        float(
                            record["total_fraud_amount"] or 0
                        ),
                        2
                    ),
                "risk_score":
                    round(
                        float(
                            record["risk_score"] or 0
                        ),
                        2
                    ),
                "risk_category":
                    record["risk_category"]
            })

        return data


# ======================================
# ACCOUNT DETAILS
# ======================================

@app.get("/account/{account_id}")
def account_details(account_id: str):

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account {id: $account_id})

    OPTIONAL MATCH
        (s)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WITH
        s,
        collect({
            transaction_id: t.id,
            receiver: r.id,
            amount: t.amount,
            fraud_status: t.fraud_status,
            fraud_pattern: t.fraud_pattern
        }) AS transactions

    RETURN
        s.id AS account,
        transactions
    """

    with driver.session() as session:

        record = session.run(
            query,
            account_id=account_id
        ).single()

        if record is None:

            return {
                "error": "Account not found",
                "account": account_id
            }

        transactions = []

        for transaction in record["transactions"]:

            if transaction["transaction_id"] is not None:

                transactions.append({
                    "transaction_id":
                        transaction["transaction_id"],

                    "receiver":
                        transaction["receiver"],

                    "amount":
                        round(
                            float(
                                transaction["amount"] or 0
                            ),
                            2
                        ),

                    "fraud_status":
                        transaction["fraud_status"],

                    "fraud_pattern":
                        transaction["fraud_pattern"]
                })

        fraud_transactions = [
            transaction
            for transaction in transactions
            if transaction["fraud_status"] == "FRAUD"
        ]

        total_fraud_amount = sum(
            transaction["amount"]
            for transaction in fraud_transactions
        )

        return {
            "account": record["account"],
            "total_transactions":
                len(transactions),
            "fraud_transactions":
                len(fraud_transactions),
            "total_fraud_amount":
                round(
                    total_fraud_amount,
                    2
                ),
            "transactions":
                transactions
        }


# ======================================
# FRAUD ALERTS
# ======================================

@app.get("/alerts")
def alerts():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WHERE t.fraud_status = 'FRAUD'

    WITH
        s,
        collect(DISTINCT r.id) AS receivers,
        count(t) AS fraud_transactions,
        sum(t.amount) AS total_fraud_amount

    WITH
        s,
        receivers,
        fraud_transactions,
        total_fraud_amount,

        (
            fraud_transactions * 10 +
            size(receivers) * 15 +
            total_fraud_amount / 1000
        ) AS risk_score

    WITH
        s,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        risk_score,

        CASE
            WHEN risk_score >= 40 THEN 'CRITICAL'
            WHEN risk_score >= 30 THEN 'HIGH'
            WHEN risk_score >= 20 THEN 'MEDIUM'
            ELSE 'LOW'
        END AS risk_category

    WHERE risk_score >= 30

    RETURN
        s.id AS account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        risk_score,
        risk_category

    ORDER BY risk_score DESC

    LIMIT 100
    """

    with driver.session() as session:

        result = session.run(query)

        data = []

        for record in result:

            data.append({
                "account":
                    record["account"],

                "receivers":
                    record["receivers"],

                "fraud_transactions":
                    record["fraud_transactions"],

                "total_fraud_amount":
                    round(
                        float(
                            record[
                                "total_fraud_amount"
                            ] or 0
                        ),
                        2
                    ),

                "risk_score":
                    round(
                        float(
                            record["risk_score"] or 0
                        ),
                        2
                    ),

                "risk_category":
                    record["risk_category"]
            })

        return {
            "count": len(data),
            "alerts": data
        }


# ======================================
# FRAUD NETWORK
# ======================================

@app.get("/fraud-network")
def fraud_network():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)

    WHERE t.fraud_status = 'FRAUD'

    RETURN
        s.id AS sender,
        t.id AS transaction,
        r.id AS receiver,
        t.amount AS amount,
        t.fraud_pattern AS fraud_pattern

    ORDER BY t.amount DESC

    LIMIT 100
    """

    with driver.session() as session:

        result = session.run(query)

        nodes = {}
        edges = []

        for record in result:

            sender = record["sender"]
            transaction = record["transaction"]
            receiver = record["receiver"]

            amount = float(
                record["amount"] or 0
            )

            if sender not in nodes:

                nodes[sender] = {
                    "id": sender,
                    "label": sender,
                    "type": "ACCOUNT"
                }

            if transaction not in nodes:

                nodes[transaction] = {
                    "id": transaction,
                    "label": transaction,
                    "type": "TRANSACTION"
                }

            if receiver not in nodes:

                nodes[receiver] = {
                    "id": receiver,
                    "label": receiver,
                    "type": "ACCOUNT"
                }

            edges.append({
                "source": sender,
                "target": transaction,
                "relationship": "SENT",
                "amount": amount
            })

            edges.append({
                "source": transaction,
                "target": receiver,
                "relationship": "RECEIVED_BY",
                "amount": amount
            })

        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }

# ======================================
# FRAUD PATTERN ANALYSIS
# ======================================

@app.get("/fraud-patterns")
def fraud_patterns():

    if driver is None:
        return {
            "error": "NEO4J_PASSWORD environment variable is not set"
        }

    query = """
    MATCH (t:Transaction)

    WHERE t.fraud_status = 'FRAUD'

    WITH
        coalesce(t.fraud_pattern, 'Unknown') AS pattern,
        count(t) AS transaction_count,
        sum(t.amount) AS total_amount

    RETURN
        pattern,
        transaction_count,
        total_amount

    ORDER BY transaction_count DESC
    """

    with driver.session() as session:

        result = session.run(query)

        data = []

        for record in result:

            data.append({
                "pattern": record["pattern"],
                "transaction_count":
                    record["transaction_count"],
                "total_amount":
                    round(
                        float(
                            record["total_amount"] or 0
                        ),
                        2
                    )
            })

        return {
            "patterns": data
        }
# ======================================
# SHUTDOWN
# ======================================

@app.on_event("shutdown")
def shutdown():

    global driver

    if driver:
        driver.close()