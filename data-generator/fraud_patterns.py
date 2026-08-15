import random
import uuid
from datetime import datetime


def create_fraud_transaction(
    sender,
    receiver,
    amount,
    pattern
):

    return {
        "transaction_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "sender_account": sender,
        "receiver_account": receiver,
        "amount": amount,
        "sender_ip": (
            f"10.0."
            f"{random.randint(1, 20)}."
            f"{random.randint(1, 254)}"
        ),
        "country": random.choice(
            ["India", "Singapore", "UAE"]
        ),
        "transaction_type": "FRAUD",
        "fraud_pattern": pattern
    }


# SMURFING
def generate_smurfing():

    transactions = []

    for i in range(1, 11):

        transaction = create_fraud_transaction(
            f"ACC{i:03d}",
            "SHELL001",
            random.choice([9700, 9800, 9900]),
            "SMURFING"
        )

        transactions.append(transaction)

    return transactions


# STARBURST
def generate_starburst():

    transactions = []

    for i in range(51, 101):

        transaction = create_fraud_transaction(
            f"ACC{i:03d}",
            "SHELL002",
            random.choice([9700, 9800, 9900]),
            "STARBURST"
        )

        transactions.append(transaction)

    return transactions


# CIRCULAR MONEY FLOW
def generate_circular_flow():

    transactions = []

    accounts = [
        "CIRC001",
        "CIRC002",
        "CIRC003"
    ]

    for i in range(3):

        transaction = create_fraud_transaction(
            accounts[i],
            accounts[(i + 1) % 3],
            random.randint(5000, 9000),
            "CIRCULAR"
        )

        transactions.append(transaction)

    return transactions


# LAYERING
def generate_layering():

    transactions = []

    accounts = [
        "LAYER001",
        "LAYER002",
        "LAYER003",
        "LAYER004",
        "LAYER005"
    ]

    for i in range(4):

        transaction = create_fraud_transaction(
            accounts[i],
            accounts[i + 1],
            random.randint(5000, 9000),
            "LAYERING"
        )

        transactions.append(transaction)

    return transactions


if __name__ == "__main__":

    print("SMURFING")
    print("-" * 40)

    for transaction in generate_smurfing():
        print(transaction)

    print("\nSTARBURST")
    print("-" * 40)

    for transaction in generate_starburst():
        print(transaction)

    print("\nCIRCULAR FLOW")
    print("-" * 40)

    for transaction in generate_circular_flow():
        print(transaction)

    print("\nLAYERING")
    print("-" * 40)

    for transaction in generate_layering():
        print(transaction)