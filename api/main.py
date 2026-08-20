import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase


# ======================================
# Configuration
# ======================================

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = os.getenv("NEO4J_PASSWORD")


# ======================================
# FastAPI Application
# ======================================

app = FastAPI(
    title="FinGraph Fraud Detection API",
    description="API for FinGraph Neo4j fraud analysis",
    version="1.0.0"
)


# ======================================
# CORS Configuration
# ======================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================
# Neo4j Connection
# ======================================

driver = None

if PASSWORD:
    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD)
    )


# ======================================
# Health Check
# ======================================

@app.get("/")
def home():

    return {
        "project": "FinGraph",
        "status": "running",
        "service": "Fraud Detection API"
    }


# ======================================
# Statistics
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

        total = record["total_transactions"]
        fraud = record["fraud_transactions"]
        amount = record["total_fraud_amount"] or 0

        percentage = 0

        if total:
            percentage = round(
                (fraud * 100.0) / total,
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
# Fraud Transactions
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
                    float(record["amount"]),
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
# Fraud Hubs
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
                    float(record["total_fraud_amount"]),
                    2
                )
            })

        return data


# ======================================
# Risk Accounts
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
                "connected_receivers": record["connected_receivers"],
                "fraud_transactions": record["fraud_transactions"],
                "total_fraud_amount": round(
                    float(record["total_fraud_amount"]),
                    2
                ),
                "risk_score": round(
                    float(record["risk_score"]),
                    2
                ),
                "risk_category": record["risk_category"]
            })

        return data


# ======================================
# Fraud Alerts
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
                "account": record["account"],
                "receivers": record["receivers"],
                "fraud_transactions": record["fraud_transactions"],
                "total_fraud_amount": round(
                    float(record["total_fraud_amount"]),
                    2
                ),
                "risk_score": round(
                    float(record["risk_score"]),
                    2
                ),
                "risk_category": record["risk_category"]
            })

        return {
            "count": len(data),
            "alerts": data
        }


# ======================================
# Shutdown
# ======================================

@app.on_event("shutdown")
def shutdown():

    global driver

    if driver:
        driver.close()