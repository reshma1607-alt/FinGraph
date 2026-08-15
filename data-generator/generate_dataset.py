import json

from transaction_generator import (
    generate_normal_transaction
)

from fraud_patterns import (
    generate_smurfing,
    generate_starburst,
    generate_circular_flow,
    generate_layering
)


transactions = []


# 100 normal transactions
for i in range(100):

    transaction = generate_normal_transaction()

    transaction["fraud_pattern"] = "NONE"

    transactions.append(transaction)


# Fraud patterns
transactions.extend(
    generate_smurfing()
)

transactions.extend(
    generate_starburst()
)

transactions.extend(
    generate_circular_flow()
)

transactions.extend(
    generate_layering()
)


# Save JSON
with open(
    "transactions.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        transactions,
        file,
        indent=2
    )


print(
    f"Generated {len(transactions)} transactions"
)

print(
    "Saved as transactions.json"
)