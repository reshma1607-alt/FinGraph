import json
import random
import uuid
from datetime import datetime
from faker import Faker


fake = Faker()

accounts = [
    f"ACC{i:03d}"
    for i in range(1, 101)
]


def generate_normal_transaction():

    sender = random.choice(accounts)

    receiver = random.choice(accounts)

    while sender == receiver:
        receiver = random.choice(accounts)

    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "sender_account": sender,
        "receiver_account": receiver,
        "amount": round(random.uniform(100, 8000), 2),
        "sender_ip": fake.ipv4(),
        "country": fake.country(),
        "transaction_type": "NORMAL"
    }

    return transaction


if __name__ == "__main__":

    print("======================================")
    print("     FinGraph Transaction Generator")
    print("======================================")

    for i in range(10):

        transaction = generate_normal_transaction()

        print(
            json.dumps(
                transaction,
                indent=2
            )
        )