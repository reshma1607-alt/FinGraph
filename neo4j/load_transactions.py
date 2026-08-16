import json
from pathlib import Path
from neo4j import GraphDatabase


# Neo4j connection
URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
DATABASE = "fingraph"


# Get password securely
PASSWORD = input("Enter Neo4j password: ")


# Location of transactions.json
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "transactions.json"


def load_transactions():
    # Read transaction data
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        transactions = json.load(file)

    print(f"Loaded {len(transactions)} transactions.")

    # Connect to Neo4j
    driver = GraphDatabase.driver(
        URI,
        auth=(USERNAME, PASSWORD)
    )

    try:
        with driver.session(database=DATABASE) as session:

            for transaction in transactions:

                sender = transaction["sender_account"]
                receiver = transaction["receiver_account"]
                transaction_id = transaction["transaction_id"]
                amount = transaction["amount"]
                timestamp = transaction["timestamp"]
                sender_ip = transaction["sender_ip"]
                country = transaction["country"]
                transaction_type = transaction["transaction_type"]

                query = """
                MERGE (s:Account {id: $sender})
                MERGE (r:Account {id: $receiver})

                MERGE (ip:IP {address: $sender_ip})

                MERGE (s)-[:USED_IP]->(ip)

                CREATE (s)-[:TRANSFERRED_TO {
                    transaction_id: $transaction_id,
                    amount: $amount,
                    timestamp: $timestamp,
                    country: $country,
                    transaction_type: $transaction_type
                }]->(r)
                """

                session.run(
                    query,
                    sender=sender,
                    receiver=receiver,
                    sender_ip=sender_ip,
                    transaction_id=transaction_id,
                    amount=amount,
                    timestamp=timestamp,
                    country=country,
                    transaction_type=transaction_type
                )

        print("======================================")
        print("Transactions loaded successfully!")
        print("======================================")

    finally:
        driver.close()


if __name__ == "__main__":
    load_transactions()