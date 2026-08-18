import json
from kafka import KafkaConsumer


KAFKA_SERVER = "localhost:9092"
TOPIC = "fin-transactions"
OUTPUT_FILE = "transactions_stream.json"


consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_SERVER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="fingraph-file-bridge",
    value_deserializer=lambda value: json.loads(
        value.decode("utf-8")
    )
)


print("======================================")
print("FinGraph Kafka → File Bridge")
print("======================================")
print("Reading transactions from Kafka...")
print("Press Ctrl+C to stop.")
print()


try:
    with open(OUTPUT_FILE, "a", encoding="utf-8") as file:

        for message in consumer:

            transaction = message.value

            file.write(
                json.dumps(transaction) + "\n"
            )

            file.flush()

            print(
                f"Received: "
                f"{transaction['transaction_id']} | "
                f"{transaction['sender_account']} → "
                f"{transaction['receiver_account']} | "
                f"Amount: {transaction['amount']}"
            )


except KeyboardInterrupt:

    print("\nKafka → File bridge stopped.")


finally:
    consumer.close()