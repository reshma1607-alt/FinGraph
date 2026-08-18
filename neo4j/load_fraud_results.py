import json
import os

from neo4j import GraphDatabase


URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "YOUR_NEO4J_PASSWORD"

RESULTS_FOLDER = "fraud_results"


driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)


def load_transaction(tx, data):

    tx.run(
        """
        MERGE (s:Account {id: $sender})
        MERGE (r:Account {id: $receiver})

        MERGE (t:Transaction {id: $transaction_id})
        SET
            t.amount = $amount,
            t.country = $country,
            t.transaction_type = $transaction_type,
            t.fraud_pattern = $fraud_pattern,
            t.fraud_status = $fraud_status

        MERGE (s)-[:SENT]->(t)
        MERGE (t)-[:RECEIVED_BY]->(r)
        """,
        transaction_id=data["transaction_id"],
        sender=data["sender_account"],
        receiver=data["receiver_account"],
        amount=data["amount"],
        country=data["country"],
        transaction_type=data["transaction_type"],
        fraud_pattern=data["fraud_pattern"],
        fraud_status=data["fraud_status"]
    )


def main():

    print("======================================")
    print("FinGraph → Neo4j Fraud Loader")
    print("======================================")

    files = [
        f for f in os.listdir(RESULTS_FOLDER)
        if not f.startswith(".")
    ]

    if not files:
        print("No fraud result file found.")
        driver.close()
        return

    file_path = os.path.join(
        RESULTS_FOLDER,
        files[0]
    )

    count = 0

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as file:

        with driver.session() as session:

            for line in file:

                if not line.strip():
                    continue

                data = json.loads(line)

                session.execute_write(
                    load_transaction,
                    data
                )

                count += 1

    driver.close()

    print()
    print(f"Loaded {count} transactions into Neo4j.")

    print()
    print("======================================")
    print("Neo4j Loading Completed")
    print("======================================")


if __name__ == "__main__":
    main()