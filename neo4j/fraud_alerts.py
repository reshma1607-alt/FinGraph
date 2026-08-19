import json
import os
from datetime import datetime
from neo4j import GraphDatabase


# ==============================
# Neo4j Configuration
# ==============================

URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = os.getenv("NEO4J_PASSWORD")


# ==============================
# Alert Generation
# ==============================

def get_fraud_alerts(driver):

    query = """
    MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
    WHERE t.fraud_status = 'FRAUD'

    WITH
        s,
        collect(DISTINCT r.id) AS receivers,
        count(t) AS fraud_transactions,
        sum(t.amount) AS total_fraud_amount

    UNWIND receivers AS receiver

    OPTIONAL MATCH (other:Account)-[:SENT]->(ft:Transaction)-[:RECEIVED_BY]->(hub:Account)
    WHERE ft.fraud_status = 'FRAUD'
      AND hub.id = receiver

    WITH
        s,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        count(DISTINCT hub) AS fraud_hubs

    WITH
        s,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        fraud_hubs,
        (
            fraud_transactions * 10 +
            size(receivers) * 15 +
            total_fraud_amount / 1000 +
            fraud_hubs * 10
        ) AS risk_score

    RETURN
        s.id AS account,
        receivers,
        fraud_transactions,
        total_fraud_amount,
        fraud_hubs,
        risk_score

    ORDER BY risk_score DESC
    """


    with driver.session() as session:

        result = session.run(query)

        alerts = []

        for record in result:

            risk_score = float(record["risk_score"])

            if risk_score >= 40:
                category = "CRITICAL"
            elif risk_score >= 30:
                category = "HIGH"
            elif risk_score >= 20:
                category = "MEDIUM"
            else:
                category = "LOW"

            if category in ("CRITICAL", "HIGH"):

                alerts.append({
                    "alert_id": f"ALERT-{len(alerts) + 1:04d}",
                    "timestamp": datetime.now().isoformat(),
                    "account": record["account"],
                    "receivers": record["receivers"],
                    "fraud_transactions": record["fraud_transactions"],
                    "total_fraud_amount": round(
                        float(record["total_fraud_amount"]), 2
                    ),
                    "fraud_hubs": record["fraud_hubs"],
                    "risk_score": round(risk_score, 2),
                    "risk_category": category
                })

        return alerts


# ==============================
# Main
# ==============================

def main():

    print("======================================")
    print("FinGraph Improved Fraud Alert Engine")
    print("======================================")

    if not PASSWORD:
        print("ERROR: NEO4J_PASSWORD environment variable is not set.")
        print()
        print("Run:")
        print('$env:NEO4J_PASSWORD="your_password"')
        return

    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD)
    )

    try:

        alerts = get_fraud_alerts(driver)

        with open(
            "fraud_alerts.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                alerts,
                file,
                indent=4
            )

        print()
        print(f"Generated {len(alerts)} fraud alerts.")
        print("Output file: fraud_alerts.json")
        print()

        for alert in alerts[:10]:

            print(
                f"[{alert['risk_category']}] "
                f"{alert['account']} | "
                f"Risk Score: {alert['risk_score']} | "
                f"Fraud Amount: "
                f"{alert['total_fraud_amount']} | "
                f"Fraud Hubs: "
                f"{alert['fraud_hubs']}"
            )

        print()
        print("======================================")
        print("Improved Fraud Alert Generation Completed")
        print("======================================")

    finally:

        driver.close()


if __name__ == "__main__":
    main()