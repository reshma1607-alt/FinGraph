import json
import time
from pathlib import Path

from kafka import KafkaProducer


# Kafka configuration
KAFKA_SERVER = "localhost:9092"
TOPIC = "fin-transactions"


# Find transactions.json
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "transactions.json"


# Create Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda value: json.dumps(value).encode("utf-8")
)


def send_transactions():

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        transactions = json.load(file)

    print(f"Loaded {len(transactions)} transactions.")

    for transaction in transactions:

        producer.send(
            TOPIC,
            value=transaction
        )

        print(
            f"Sent: {transaction['transaction_id']} | "
            f"{transaction['sender_account']} -> "
            f"{transaction['receiver_account']} | "
            f"{transaction['amount']}"
        )

        time.sleep(0.1)

    producer.flush()

    print("======================================")
    print("All transactions sent to Kafka!")
    print("======================================")


if __name__ == "__main__":
    send_transactions()