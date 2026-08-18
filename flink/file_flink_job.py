from pyflink.table import EnvironmentSettings, TableEnvironment


def main():

    print("======================================")
    print("FinGraph Real Transaction Fraud Detection")
    print("======================================")

    settings = EnvironmentSettings.in_batch_mode()
    table_env = TableEnvironment.create(settings)

    # Read real transactions saved from Kafka
    table_env.execute_sql("""
        CREATE TEMPORARY TABLE transactions (
            transaction_id STRING,
            event_time STRING,
            sender_account STRING,
            receiver_account STRING,
            amount DOUBLE,
            sender_ip STRING,
            country STRING,
            transaction_type STRING,
            fraud_pattern STRING
        ) WITH (
            'connector' = 'filesystem',
            'path' = 'transactions_stream.json',
            'format' = 'json'
        )
    """)

    # Create fraud detection result
    result = table_env.sql_query("""
        SELECT
            transaction_id,
            sender_account,
            receiver_account,
            amount,
            country,
            transaction_type,
            fraud_pattern,

            CASE
                WHEN fraud_pattern <> 'NONE'
                    THEN 'FRAUD'

                WHEN receiver_account LIKE 'SHELL%'
                     AND amount >= 9000
                    THEN 'FRAUD'

                WHEN transaction_type <> 'NORMAL'
                    THEN 'SUSPICIOUS'

                WHEN amount >= 9000
                    THEN 'HIGH_RISK'

                WHEN amount >= 7000
                    THEN 'MEDIUM_RISK'

                ELSE 'LOW_RISK'
            END AS fraud_status

        FROM transactions
    """)

    # Create output table
    table_env.execute_sql("""
        CREATE TEMPORARY TABLE fraud_results (
            transaction_id STRING,
            sender_account STRING,
            receiver_account STRING,
            amount DOUBLE,
            country STRING,
            transaction_type STRING,
            fraud_pattern STRING,
            fraud_status STRING
        ) WITH (
            'connector' = 'filesystem',
            'path' = 'fraud_results',
            'format' = 'json'
        )
    """)

    # Write results to fraud_results folder
    result.execute_insert("fraud_results").wait()

    print("\n======================================")
    print("Fraud results saved successfully!")
    print("Output folder: fraud_results")
    print("======================================")


if __name__ == "__main__":
    main()