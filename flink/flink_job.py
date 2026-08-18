from pyflink.table import EnvironmentSettings, TableEnvironment


def main():

    print("======================================")
    print("FinGraph Flink Risk Analytics")
    print("======================================")

    settings = EnvironmentSettings.in_batch_mode()
    table_env = TableEnvironment.create(settings)

    # Create a temporary table using Flink's built-in datagen connector
    table_env.execute_sql("""
        CREATE TEMPORARY TABLE transactions (
            transaction_id STRING,
            sender STRING,
            receiver STRING,
            amount DOUBLE
        ) WITH (
            'connector' = 'datagen',
            'number-of-rows' = '4',
            'fields.transaction_id.kind' = 'sequence',
            'fields.transaction_id.start' = '1',
            'fields.transaction_id.end' = '4',
            'fields.sender.kind' = 'random',
            'fields.sender.length' = '1',
            'fields.receiver.kind' = 'random',
            'fields.receiver.length' = '1',
            'fields.amount.kind' = 'random',
            'fields.amount.min' = '1000',
            'fields.amount.max' = '10000'
        )
    """)

    # Process transactions with Flink SQL
    result = table_env.execute_sql("""
        SELECT
            transaction_id,
            sender,
            receiver,
            amount,
            CASE
                WHEN amount >= 9000 THEN 'HIGH'
                WHEN amount >= 7000 THEN 'MEDIUM'
                ELSE 'LOW'
            END AS risk_level
        FROM transactions
    """)

    print("\nProcessed Transactions:")
    print("--------------------------------------")

    result.print()

    print("\n======================================")
    print("FinGraph Flink Risk Processing Completed")
    print("======================================")


if __name__ == "__main__":
    main()