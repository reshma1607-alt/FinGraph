from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
import os
from typing import Optional

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
    "bolt://localhost:7687"
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
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    RETURN
        coalesce(
            t.transaction_id,
            elementId(t)
        ) AS transaction_id,

        coalesce(
            t.sender_account,
            t.sender,
            'Unknown'
        ) AS sender,

        coalesce(
            t.receiver_account,
            t.receiver,
            'Unknown'
        ) AS receiver,

        coalesce(t.amount, 0) AS amount,

        coalesce(t.country, 'Unknown')
            AS country,

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
                    record["transaction_id"],
                "sender":
                    record["sender"],
                "receiver":
                    record["receiver"],
                "amount":
                    safe_float(record["amount"]),
                "country":
                    record["country"],
                "fraud_pattern":
                    record["fraud_pattern"],
                "timestamp":
                    str(record["timestamp"])
            })

        return {
            "transactions": transactions,
            "count": len(transactions)
        }

    except Exception as error:
        return {
            "error": str(error)
        }


# ==========================================
# FRAUD ALERTS
# ==========================================

@app.get("/alerts")
def alerts():

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
            t.sender_account,
            t.sender,
            'Unknown'
        ) AS account,

        collect(
            DISTINCT coalesce(
                t.receiver_account,
                t.receiver,
                'Unknown'
            )
        ) AS receivers,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS total_fraud_amount,

        sum(
            coalesce(t.amount, 0)
        ) +
        (count(t) * 1000) +
        (size(collect(DISTINCT
            coalesce(
                t.receiver_account,
                t.receiver,
                'Unknown'
            )
        )) * 500) AS raw_risk_score

    WITH
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        CASE
            WHEN raw_risk_score > 100000
                THEN 100
            WHEN raw_risk_score / 1000.0 > 100
                THEN 100
            ELSE round(
                raw_risk_score / 1000.0,
                2
            )
        END AS risk_score

    RETURN
        account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
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

    ORDER BY risk_score DESC
    """

    try:
        records = run_query(query)

        result = []

        for record in records:
            result.append({
                "account":
                    record["account"],
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
                "risk_score":
                    safe_float(
                        record["risk_score"]
                    ),
                "risk_category":
                    record["risk_category"]
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

    query = """
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.sender_account,
            t.sender,
            'Unknown'
        ) AS account,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS total_fraud_amount,

        collect(
            DISTINCT coalesce(
                t.receiver_account,
                t.receiver,
                'Unknown'
            )
        ) AS receivers

    WITH
        account,
        fraud_transactions,
        total_fraud_amount,
        receivers,

        (
            fraud_transactions * 10
            +
            size(receivers) * 5
            +
            CASE
                WHEN total_fraud_amount >= 100000
                    THEN 50
                WHEN total_fraud_amount >= 50000
                    THEN 30
                WHEN total_fraud_amount >= 10000
                    THEN 15
                ELSE 5
            END
        ) AS raw_score

    WITH
        account,
        fraud_transactions,
        total_fraud_amount,
        receivers,

        CASE
            WHEN raw_score > 100
                THEN 100
            ELSE raw_score
        END AS risk_score

    RETURN
        account,
        fraud_transactions,
        total_fraud_amount,
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
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.receiver_account,
            t.receiver,
            'Unknown'
        ) AS fraud_hub,

        count(
            DISTINCT coalesce(
                t.sender_account,
                t.sender
            )
        ) AS unique_senders,

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
    MATCH (t:Transaction)

    WHERE
        coalesce(
            t.sender_account,
            t.sender
        ) = $account_id

        OR

        coalesce(
            t.receiver_account,
            t.receiver
        ) = $account_id

    WITH
        collect(t) AS transactions

    RETURN
        size(transactions)
            AS total_transactions,

        size([
            x IN transactions
            WHERE coalesce(
                x.fraud_status,
                x.transaction_type
            ) = 'FRAUD'
        ])
            AS fraud_transactions,

        reduce(
            total = 0.0,
            x IN transactions |
            total +
            CASE
                WHEN coalesce(
                    x.fraud_status,
                    x.transaction_type
                ) = 'FRAUD'
                THEN coalesce(x.amount, 0)
                ELSE 0
            END
        )
            AS total_fraud_amount,

        [
            x IN transactions |
            {
                transaction_id:
                    coalesce(
                        x.transaction_id,
                        elementId(x)
                    ),

                receiver:
                    coalesce(
                        x.receiver_account,
                        x.receiver,
                        'Unknown'
                    ),

                amount:
                    coalesce(x.amount, 0),

                fraud_status:
                    coalesce(
                        x.fraud_status,
                        x.transaction_type,
                        'UNKNOWN'
                    ),

                fraud_pattern:
                    coalesce(
                        x.fraud_pattern,
                        'Unknown'
                    )
            }
        ][0..50]
            AS transaction_details
    """

    try:
        records = run_query(
            query,
            {"account_id": account_id}
        )

        if not records:
            return {
                "error":
                    "Account not found"
            }

        record = records[0]

        transactions = []

        for item in (
            record["transaction_details"]
            or []
        ):
            transactions.append({
                "transaction_id":
                    item["transaction_id"],
                "receiver":
                    item["receiver"],
                "amount":
                    safe_float(item["amount"]),
                "fraud_status":
                    item["fraud_status"],
                "fraud_pattern":
                    item["fraud_pattern"]
            })

        return {
            "account":
                account_id,
            "total_transactions":
                int(
                    record["total_transactions"]
                    or 0
                ),
            "fraud_transactions":
                int(
                    record["fraud_transactions"]
                    or 0
                ),
            "total_fraud_amount":
                safe_float(
                    record["total_fraud_amount"]
                ),
            "transactions":
                transactions
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

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH
        coalesce(
            t.timestamp,
            t.date
        ) AS transaction_date,

        count(t) AS fraud_transactions,

        sum(
            coalesce(t.amount, 0)
        ) AS fraud_amount

    RETURN
        transaction_date,
        fraud_transactions,
        fraud_amount

    ORDER BY transaction_date
    """

    try:
        records = run_query(query)

        data = []

        for record in records:
            data.append({
                "date":
                    str(
                        record["transaction_date"]
                    )
                    if record["transaction_date"]
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
    MATCH (t:Transaction)

    WHERE coalesce(
        t.fraud_status,
        t.transaction_type
    ) = 'FRAUD'

    WITH t
    LIMIT 250

    OPTIONAL MATCH (s:Account)
    WHERE
        s.account_id =
        coalesce(
            t.sender_account,
            t.sender
        )

    OPTIONAL MATCH (r:Account)
    WHERE
        r.account_id =
        coalesce(
            t.receiver_account,
            t.receiver
        )

    RETURN
        t,
        s,
        r
    """

    try:
        records = run_query(query)

        nodes = {}
        edges = []

        for record in records:

            transaction = record["t"]
            sender_node = record["s"]
            receiver_node = record["r"]

            transaction_id = str(
                transaction.get(
                    "transaction_id",
                    transaction.element_id
                )
            )

            sender = (
                transaction.get(
                    "sender_account"
                )
                or transaction.get("sender")
                or "Unknown"
            )

            receiver = (
                transaction.get(
                    "receiver_account"
                )
                or transaction.get("receiver")
                or "Unknown"
            )

            amount = safe_float(
                transaction.get("amount", 0)
            )

            sender_id = f"ACCOUNT:{sender}"
            receiver_id = f"ACCOUNT:{receiver}"
            transaction_node_id = (
                f"TRANSACTION:{transaction_id}"
            )

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

            nodes[transaction_node_id] = {
                "id": transaction_node_id,
                "label": transaction_id[:12],
                "type": "TRANSACTION"
            }

            edges.append({
                "source":
                    sender_id,
                "target":
                    transaction_node_id,
                "amount":
                    amount
            })

            edges.append({
                "source":
                    transaction_node_id,
                "target":
                    receiver_id,
                "amount":
                    amount
            })

        return {
            "nodes":
                list(nodes.values()),
            "edges":
                edges
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