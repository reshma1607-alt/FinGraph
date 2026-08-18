import json

from pyflink.common import WatermarkStrategy, Types
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer,
)
from pyflink.common.serialization import SimpleStringSchema


def main():

    print("======================================")
    print("FinGraph Kafka → Flink")
    print("======================================")

    env = StreamExecutionEnvironment.get_execution_environment()

    # Read from the existing Kafka topic
    kafka_source = (
        KafkaSource.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_topics("fin-transactions")
        .set_group_id("fingraph-flink")
        .set_starting_offsets(
            KafkaOffsetsInitializer.earliest()
        )
        .set_value_only_deserializer(
            SimpleStringSchema()
        )
        .build()
    )

    transactions = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),
        "FinGraph Kafka Source"
    )

    # Print the real JSON transactions received from Kafka
    transactions.print()

    env.execute("FinGraph Kafka to Flink")


if __name__ == "__main__":
    main()