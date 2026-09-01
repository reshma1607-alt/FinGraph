from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# FINGRAPH - FRAUD INTELLIGENCE BACKEND
# ==========================================

app = FastAPI(
    title="FinGraph Fraud Intelligence API",
    version="1.0.0"
)

# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# NEO4J CONFIGURATION
# ==========================================

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "neo4j://127.0.0.1:7687"
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j"
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD"
)

driver = None

if NEO4J_PASSWORD:
    try:
        driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
    except Exception:
        driver = None


# ==========================================
# HELPERS
# ==========================================

def neo4j_error():
    return {
        "error": (
            "Neo4j connection is not available. "
            "Check NEO4J_URI, NEO4J_USER, "
            "NEO4J_PASSWORD and make sure Neo4j "
            "is running on port 7687."
        )
    }


def run_query(query, parameters=None):
    if driver is None:
        return None

    with driver.session() as session:
        return list(
            session.run(
                query,
                parameters or {}
            )
        )


def safe_float(value):
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


# ==========================================
# ROOT / HEALTH
# ==========================================

@app.get("/")
def root():
    return {
        "name": "FinGraph",
        "status": "running",
        "service": "Fraud Intelligence API"
    }


@app.get("/health")
def health():
    if driver is None:
        return {
            "status": "error",
            "neo4j": "disconnected"
        }

    try:
        with driver.session() as session:
            session.run("RETURN 1").single()

        return {
            "status": "ok",
            "neo4j": "connected"
        }

    except Exception as error:
        return {
            "status": "error",
            "neo4j": "disconnected",
            "message": str(error)
        }


# ==========================================
# STATISTICS
# ==========================================

@app.get("/statistics")
def statistics():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (t:Transaction)

    WITH
        count(t) AS total_transactions,
        sum(
            CASE
                WHEN coalesce(
                    t.fraud_status,
                    t.transaction_type
                ) = 'FRAUD'
                THEN 1
                ELSE 0
            END
        ) AS fraud_transactions,
        sum(
            CASE
                WHEN coalesce(
                    t.fraud_status,
                    t.transaction_type
                ) = 'FRAUD'
                THEN coalesce(t.amount, 0)
                ELSE 0
            END
        ) AS total_fraud_amount

    RETURN
        total_transactions,
        fraud_transactions,
        total_fraud_amount
    """

    try:
        record = run_query(query)[0]

        total = int(
            record["total_transactions"] or 0
        )

        fraud = int(
            record["fraud_transactions"] or 0
        )

        percentage = (
            round((fraud / total) * 100, 2)
            if total
            else 0
        )

        return {
            "total_transactions": total,
            "fraud_transactions": fraud,
            "fraud_percentage": percentage,
            "total_fraud_amount":
                safe_float(
                    record["total_fraud_amount"]
                )
        }

    except Exception as error:
        return {
            "error": str(error)
        }


# ==========================================
# FRAUD TRANSACTIONS
# ==========================================

@app.get("/fraud")
def fraud_transactions():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (sender:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(receiver:Account)

    WHERE
        t.fraud_status = 'FRAUD'
        OR
        t.transaction_type = 'FRAUD'

    RETURN
        coalesce(
            t.transaction_id,
            elementId(t)
        ) AS transaction_id,

        coalesce(
            sender.account_id,
            sender.account,
            sender.id,
            elementId(sender)
        ) AS sender,

        coalesce(
            receiver.account_id,
            receiver.account,
            receiver.id,
            elementId(receiver)
        ) AS receiver,

        coalesce(
            t.amount,
            0
        ) AS amount,

        coalesce(
            t.country,
            'Unknown'
        ) AS country,

        coalesce(
            t.fraud_pattern,
            'Unknown'
        ) AS fraud_pattern,

        coalesce(
            t.timestamp,
            t.date,
            ''
        ) AS timestamp

    ORDER BY amount DESC
    """

    try:

        records = run_query(query)

        transactions = []

        for record in records:

            transactions.append({
                "transaction_id":
                    str(record["transaction_id"]),

                "sender":
                    str(record["sender"]),

                "receiver":
                    str(record["receiver"]),

                "amount":
                    safe_float(
                        record["amount"]
                    ),

                "country":
                    str(record["country"]),

                "fraud_pattern":
                    str(record["fraud_pattern"]),

                "timestamp":
                    str(record["timestamp"])
            })

        return {
            "transactions":
                transactions,

            "count":
                len(transactions)
        }

    except Exception as error:

        return {
            "error":
                str(error)
        }
# ==========================================
# FRAUD ALERTS
# ==========================================

@app.get("/alerts")
def alerts():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (sender:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(receiver:Account)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        sender,
        receiver,
        t

    // Count how many different fraudulent senders
    // are connected to each receiver
    WITH
        receiver,
        collect(DISTINCT sender) AS connected_senders,
        collect(t) AS fraud_transactions_list

    WITH
        receiver,
        size(connected_senders) AS hub_senders,
        fraud_transactions_list

    UNWIND fraud_transactions_list AS t

    WITH
        receiver,
        hub_senders,
        t

    // Group transactions by sender account
    MATCH (sender:Account)-[:SENT]->(t)

    WITH
        sender,
        receiver,
        hub_senders,
        t

    WITH
        coalesce(
            sender.account_id,
            sender.id,
            elementId(sender)
        ) AS account,

        collect(
            DISTINCT coalesce(
                receiver.account_id,
                receiver.id,
                elementId(receiver)
            )
        ) AS receivers,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS total_fraud_amount,

        max(hub_senders) AS max_hub_senders

    WITH
        account,
        [x IN receivers WHERE x IS NOT NULL] AS receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,

        (
            (total_fraud_amount / 1000.0)
            + (fraud_transactions * 15)
            + (
                size(
                    [x IN receivers WHERE x IS NOT NULL]
                ) * 10
            )
        ) AS base_risk

    WITH
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,
        base_risk,

        CASE

            // Very strong fraud hub
            WHEN max_hub_senders >= 50
                THEN 35

            // Strong fraud hub
            WHEN max_hub_senders >= 10
                THEN 20

            // Moderate fraud hub
            WHEN max_hub_senders >= 5
                THEN 10

            ELSE 0

        END AS network_risk

    WITH
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,

        base_risk + network_risk AS raw_risk_score

    WITH
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,

        CASE
            WHEN raw_risk_score >= 100
                THEN 100

            ELSE round(
                raw_risk_score,
                2
            )

        END AS risk_score

    WITH
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,
        risk_score,

        CASE

            WHEN risk_score >= 80
                THEN 'CRITICAL'

            WHEN risk_score >= 60
                THEN 'HIGH'

            WHEN risk_score >= 30
                THEN 'MEDIUM'

            ELSE 'LOW'

        END AS risk_category

    RETURN
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        max_hub_senders,
        risk_score,
        risk_category

    ORDER BY
        risk_score DESC
    """

    try:

        records = run_query(query)

        result = []

        for record in records:

            result.append({

                "account":
                    str(record["account"]),

                "receivers":
                    record["receivers"] or [],

                "fraud_transactions":
                    int(
                        record["fraud_transactions"] or 0
                    ),

                "total_fraud_amount":
                    safe_float(
                        record["total_fraud_amount"]
                    ),

                "hub_senders":
                    int(
                        record["max_hub_senders"] or 0
                    ),

                "risk_score":
                    safe_float(
                        record["risk_score"]
                    ),

                "risk_category":
                    str(
                        record["risk_category"]
                    )

            })

        return {
            "alerts": result,
            "count": len(result)
        }

    except Exception as error:

        return {
            "error": str(error)
        }
# ==========================================
# RISK ACCOUNTS
# ==========================================

@app.get("/risk-accounts")
def risk_accounts():

    if driver is None:
        return neo4j_error()

    query ="""
MATCH (account:Account)-[:SENT]->(t:Transaction)

WHERE coalesce(
    t.fraud_status,
    t.transaction_type
) = 'FRAUD'

WITH
    account.id AS account,
    count(t) AS fraud_transactions,
    sum(coalesce(t.amount, 0)) AS total_fraud_amount

WITH
    account,
    fraud_transactions,
    total_fraud_amount,

    (
        fraud_transactions * 20
        +
        CASE
            WHEN total_fraud_amount >= 100000 THEN 60
            WHEN total_fraud_amount >= 50000 THEN 45
            WHEN total_fraud_amount >= 10000 THEN 30
            WHEN total_fraud_amount >= 5000 THEN 20
            ELSE 10
        END
    ) AS raw_score

WITH
    account,
    fraud_transactions,
    total_fraud_amount,

    CASE
        WHEN raw_score > 100 THEN 100
        ELSE raw_score
    END AS risk_score

RETURN
    account,
    fraud_transactions,
    total_fraud_amount,
    risk_score,

    CASE
        WHEN risk_score >= 80 THEN 'CRITICAL'
        WHEN risk_score >= 60 THEN 'HIGH'
        WHEN risk_score >= 30 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_category

ORDER BY risk_score DESC
"""
    try:
        records = run_query(query)

        result = []

        for record in records:
            result.append({
                "account":
                    record["account"],
                "fraud_transactions":
                    int(
                        record["fraud_transactions"] or 0
                    ),
                "total_fraud_amount":
                    safe_float(
                        record["total_fraud_amount"]
                    ),
                "risk_score":
                    safe_float(
                        record["risk_score"]
                    ),
                "risk_category":
                    record["risk_category"]
            })

        return result

    except Exception as error:
        return {
            "error": str(error)
        }


# ==========================================
# FRAUD HUBS
# ==========================================

@app.get("/fraud-hubs")
def fraud_hubs():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (t:Transaction)-[:RECEIVED_BY]->(hub:Account)
    MATCH (sender:Account)-[:SENT]->(t)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        hub.id AS fraud_hub,
        count(DISTINCT sender.id) AS unique_senders,
        count(t) AS fraud_transactions,
        sum(
            coalesce(t.amount, 0)
        ) AS total_fraud_amount

    RETURN
        fraud_hub,
        unique_senders,
        fraud_transactions,
        total_fraud_amount

    ORDER BY fraud_transactions DESC
    """

    try:

        records = run_query(query)

        result = []

        for record in records:

            result.append({
                "fraud_hub":
                    record["fraud_hub"],

                "unique_senders":
                    int(
                        record["unique_senders"] or 0
                    ),

                "fraud_transactions":
                    int(
                        record["fraud_transactions"] or 0
                    ),

                "total_fraud_amount":
                    safe_float(
                        record["total_fraud_amount"]
                    )
            })

        return result

    except Exception as error:

        return {
            "error": str(error)
        }
# ==========================================
# ACCOUNT DETAILS
# ==========================================

@app.get("/account/{account_id}")
def account_details(account_id: str):

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (sender:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(receiver:Account)

    WITH
        sender,
        t,
        receiver,

        coalesce(
            sender.account_id,
            sender.id,
            elementId(sender)
        ) AS sender_id,

        coalesce(
            receiver.account_id,
            receiver.id,
            elementId(receiver)
        ) AS receiver_id

    WHERE
        sender_id = $account_id
        OR receiver_id = $account_id

    WITH
        t,
        sender_id,
        receiver_id

    WITH
        collect({
            transaction_id:
                coalesce(
                    t.transaction_id,
                    elementId(t)
                ),

            sender:
                sender_id,

            receiver:
                receiver_id,

            amount:
                coalesce(
                    t.amount,
                    0
                ),

            fraud_status:
                coalesce(
                    t.fraud_status,
                    t.transaction_type,
                    'UNKNOWN'
                ),

            fraud_pattern:
                coalesce(
                    t.fraud_pattern,
                    'Unknown'
                )
        }) AS transaction_details

    RETURN
        size(transaction_details)
            AS total_transactions,

        size([
            x IN transaction_details
            WHERE x.fraud_status = 'FRAUD'
        ])
            AS fraud_transactions,

        reduce(
            total = 0.0,
            x IN transaction_details |

            total +

            CASE
                WHEN x.fraud_status = 'FRAUD'
                THEN x.amount
                ELSE 0
            END
        )
            AS total_fraud_amount,

        transaction_details[0..50]
            AS transaction_details
    """

    try:

        records = run_query(
            query,
            {
                "account_id": account_id
            }
        )

        if not records:

            return {
                "account": account_id,
                "total_transactions": 0,
                "fraud_transactions": 0,
                "total_fraud_amount": 0,
                "transactions": []
            }

        record = records[0]

        transactions = []

        for item in (
            record["transaction_details"] or []
        ):

            transactions.append({

                "transaction_id":
                    str(
                        item["transaction_id"]
                    ),

                "sender":
                    str(
                        item["sender"]
                    ),

                "receiver":
                    str(
                        item["receiver"]
                    ),

                "amount":
                    safe_float(
                        item["amount"]
                    ),

                "fraud_status":
                    str(
                        item["fraud_status"]
                    ),

                "fraud_pattern":
                    str(
                        item["fraud_pattern"]
                    )

            })

        return {

            "account":
                account_id,

            "total_transactions":
                int(
                    record[
                        "total_transactions"
                    ] or 0
                ),

            "fraud_transactions":
                int(
                    record[
                        "fraud_transactions"
                    ] or 0
                ),

            "total_fraud_amount":
                safe_float(
                    record[
                        "total_fraud_amount"
                    ]
                ),

            "transactions":
                transactions
        }

    except Exception as error:

        return {
            "error": str(error)
        }
# ==========================================
# FRAUD NETWORK
# ==========================================

@app.get("/fraud-network")
def fraud_network():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (sender:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(receiver:Account)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    RETURN
        coalesce(
            sender.account_id,
            sender.id,
            elementId(sender)
        ) AS sender,

        coalesce(
            receiver.account_id,
            receiver.id,
            elementId(receiver)
        ) AS receiver,

        coalesce(t.amount, 0) AS amount,

        coalesce(
            t.fraud_pattern,
            'UNKNOWN'
        ) AS pattern
    """

    try:

        records = run_query(query)

        nodes = {}
        edges = []

        for record in records:

            sender = record["sender"]
            receiver = record["receiver"]

            if sender not in nodes:
                nodes[sender] = {
                    "id": sender,
                    "label": sender,
                    "type": "ACCOUNT"
                }

            if receiver not in nodes:
                nodes[receiver] = {
                    "id": receiver,
                    "label": receiver,
                    "type": "HUB"
                }

            edges.append({
                "from": sender,
                "to": receiver,
                "amount": safe_float(
                    record["amount"]
                ),
                "pattern": record["pattern"]
            })

        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }

    except Exception as error:

        return {
            "error": str(error)
        }
# ==========================================
# FRAUD PATTERN ANALYSIS
# ==========================================

@app.get("/fraud-patterns")
def fraud_patterns():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.fraud_pattern,
            'Unknown'
        ) AS pattern,

        count(t) AS transaction_count,

        sum(
            coalesce(t.amount, 0)
        ) AS total_amount

    RETURN
        pattern,
        transaction_count,
        total_amount

    ORDER BY transaction_count DESC
    """

    try:
        records = run_query(query)

        data = []

        for record in records:
            data.append({
                "pattern":
                    record["pattern"],

                "transaction_count":
                    int(
                        record["transaction_count"]
                        or 0
                    ),

                "total_amount":
                    safe_float(
                        record["total_amount"]
                    )
            })

        return {
            "patterns": data
        }

    except Exception as error:
        return {
            "error": str(error)
        }


# ==========================================
# FRAUD TREND ANALYSIS
# ==========================================

@app.get("/fraud-trends")
def fraud_trends():

    if driver is None:
        return neo4j_error()

    query = """
MATCH (t:Transaction)

WITH
    coalesce(
        t.transaction_type,
        'Unknown'
    ) AS transaction_type,

    count(t) AS transactions,

    sum(
        CASE
            WHEN t.transaction_type = 'FRAUD'
            THEN coalesce(t.amount, 0)
            ELSE 0
        END
    ) AS fraud_amount

RETURN
    transaction_type AS date,
    transactions AS fraud_transactions,
    fraud_amount

ORDER BY transaction_type
"""

    try:
        records = run_query(query)

        data = []

        for record in records:
            data.append({
                "date":
                    str(
                        record["date"]
                    )
                    if record["date"]
                    else "Unknown",

                "fraud_transactions":
                    int(
                        record["fraud_transactions"]
                        or 0
                    ),

                "fraud_amount":
                    safe_float(
                        record["fraud_amount"]
                    )
            })

        return {
            "trends": data
        }

    except Exception as error:
        return {
            "error": str(error)
        }
# ==========================================
# FRAUD TRANSACTIONS BY TYPE
# ==========================================

@app.get("/fraud-transaction-types")
def fraud_transaction_types():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.transaction_type,
            'Unknown'
        ) AS transaction_type,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS fraud_amount

    RETURN
        transaction_type,
        fraud_transactions,
        fraud_amount

    ORDER BY fraud_transactions DESC
    """

    try:

        records = run_query(query)

        data = []

        for record in records:

            data.append({
                "transaction_type":
                    record["transaction_type"],

                "fraud_transactions":
                    int(
                        record["fraud_transactions"]
                        or 0
                    ),

                "fraud_amount":
                    safe_float(
                        record["fraud_amount"]
                    )
            })

        return {
            "transaction_types": data
        }

    except Exception as error:

        return {
            "error": str(error)
        }
    


# ==========================================
# COUNTRY-WISE FRAUD ANALYSIS
# ==========================================

@app.get("/fraud-countries")
def fraud_countries():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.country,
            'Unknown'
        ) AS country,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS fraud_amount

    RETURN
        country,
        fraud_transactions,
        fraud_amount

    ORDER BY fraud_transactions DESC
    """

    try:
        records = run_query(query)

        data = []

        for record in records:
            data.append({
                "country":
                    record["country"],

                "fraud_transactions":
                    int(
                        record["fraud_transactions"]
                        or 0
                    ),

                "fraud_amount":
                    safe_float(
                        record["fraud_amount"]
                    )
            })

        return {
            "countries": data
        }

    except Exception as error:
        return {
            "error": str(error)
        }

# ==========================================
# FRAUD NETWORK
# ==========================================

@app.get("/fraud-network")
def fraud_network():

    if driver is None:
        return neo4j_error()

    query = """
    MATCH (sender:Account)-[:SENT]-(t:Transaction)-[:RECEIVED_BY]-(receiver:Account)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    RETURN
        sender.id AS sender_id,
        receiver.id AS receiver_id,
        t

    LIMIT 250
    """

    try:

        records = run_query(query)

        nodes = {}
        edges = []

        for record in records:

            transaction = record["t"]

            sender = (
                record["sender_id"]
                or "Unknown"
            )

            receiver = (
                record["receiver_id"]
                or "Unknown"
            )

            transaction_id = str(
                transaction.get(
                    "transaction_id",
                    transaction.element_id
                )
            )

            amount = safe_float(
                transaction.get("amount", 0)
            )

            sender_id = f"ACCOUNT:{sender}"

            receiver_id = f"ACCOUNT:{receiver}"

            transaction_node_id = (
                f"TRANSACTION:{transaction_id}"
            )

            # -------------------------------
            # ACCOUNT NODES
            # -------------------------------

            nodes[sender_id] = {
                "id": sender_id,
                "label": str(sender),
                "type": "ACCOUNT"
            }

            nodes[receiver_id] = {
                "id": receiver_id,
                "label": str(receiver),
                "type": "ACCOUNT"
            }

            # -------------------------------
            # TRANSACTION NODE
            # -------------------------------

            nodes[transaction_node_id] = {
                "id": transaction_node_id,
                "label": transaction_id[:12],
                "type": "TRANSACTION"
            }

            # -------------------------------
            # SENDER → TRANSACTION
            # -------------------------------

            edges.append({
                "source": sender_id,
                "target": transaction_node_id,
                "amount": amount
            })

            # -------------------------------
            # TRANSACTION → RECEIVER
            # -------------------------------

            edges.append({
                "source": transaction_node_id,
                "target": receiver_id,
                "amount": amount
            })

        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }

    except Exception as error:

        return {
            "error": str(error)
        }

# ==========================================
# SHUTDOWN
# ==========================================

@app.on_event("shutdown")
def shutdown_event():

    global driver

    if driver is not None:
        driver.close()
        driver = None


# ==========================================
# LOCAL RUN
# ==========================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )