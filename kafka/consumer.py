import json
from kafka import KafkaConsumer

KAFKA_SERVER = "localhost:9092"
TOPIC = "fin-transactions"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_SERVER,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    group_id="fingraph-consumer",
    value_deserializer=lambda value: json.loads(value.decode("utf-8"))
)

print("======================================")
print("FinGraph Kafka Consumer Started")
print("Waiting for transactions...")
print("======================================")

try:
    for message in consumer:
        transaction = message.value

        print(
            f"Received: {transaction['transaction_id']} | "
            f"{transaction['sender_account']} -> "
            f"{transaction['receiver_account']} | "
            f"Amount: {transaction['amount']}"
        )

except KeyboardInterrupt:
    print("\nConsumer stopped.")

finally:
    consumer.close()