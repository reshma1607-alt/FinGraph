// 1. Total transactions and fraud count
MATCH (t:Transaction)
RETURN
    count(t) AS total_transactions,
    count(CASE WHEN t.fraud_status = 'FRAUD' THEN 1 END) AS fraud_transactions,
    round(
        100.0 * count(CASE WHEN t.fraud_status = 'FRAUD' THEN 1 END)
        / count(t),
        2
    ) AS fraud_percentage;


// 2. Fraud hotspots
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
WITH
    r,
    count(DISTINCT s) AS unique_senders,
    count(t) AS fraud_transactions,
    sum(t.amount) AS total_fraud_amount
RETURN
    r.id AS receiver,
    unique_senders,
    fraud_transactions,
    round(total_fraud_amount, 2) AS total_fraud_amount
ORDER BY unique_senders DESC, total_fraud_amount DESC;


// 3. Highest-risk sender accounts
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
WITH
    s,
    count(t) AS fraud_transactions,
    count(DISTINCT r) AS fraud_receivers,
    sum(t.amount) AS total_fraud_amount
WITH
    s,
    fraud_transactions,
    fraud_receivers,
    total_fraud_amount,
    (
        fraud_transactions * 10 +
        fraud_receivers * 15 +
        total_fraud_amount / 1000
    ) AS risk_score
RETURN
    s.id AS account,
    fraud_transactions,
    fraud_receivers,
    round(total_fraud_amount, 2) AS total_fraud_amount,
    round(risk_score, 2) AS risk_score,
    CASE
        WHEN risk_score >= 100 THEN 'CRITICAL'
        WHEN risk_score >= 75 THEN 'HIGH'
        WHEN risk_score >= 50 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_category
ORDER BY risk_score DESC
LIMIT 20;


// 4. Highest-value fraud transactions
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
RETURN
    t.id AS transaction_id,
    s.id AS sender,
    r.id AS receiver,
    round(t.amount, 2) AS amount,
    t.country AS country,
    t.fraud_pattern AS fraud_pattern
ORDER BY t.amount DESC
LIMIT 20;
// 5. Account risk investigation
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
WITH
    s,
    collect(DISTINCT r.id) AS receivers,
    count(t) AS fraud_transactions,
    sum(t.amount) AS total_fraud_amount
WITH
    s,
    receivers,
    fraud_transactions,
    total_fraud_amount,
    (
        fraud_transactions * 10 +
        size(receivers) * 15 +
        total_fraud_amount / 1000
    ) AS risk_score
RETURN
    s.id AS account,
    size(receivers) AS connected_receivers,
    fraud_transactions,
    round(total_fraud_amount, 2) AS total_fraud_amount,
    round(risk_score, 2) AS risk_score,
    CASE
        WHEN risk_score >= 100 THEN 'CRITICAL'
        WHEN risk_score >= 75 THEN 'HIGH'
        WHEN risk_score >= 50 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS risk_category
ORDER BY risk_score DESC
LIMIT 20;


// 6. Fraud sender-receiver relationships
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
WITH
    s.id AS sender,
    r.id AS receiver,
    count(t) AS fraud_transactions,
    sum(t.amount) AS total_fraud_amount
RETURN
    sender,
    receiver,
    fraud_transactions,
    round(total_fraud_amount, 2) AS total_fraud_amount
ORDER BY total_fraud_amount DESC
LIMIT 20;


// 7. Fraud hotspots
MATCH (s:Account)-[:SENT]->(t:Transaction)-[:RECEIVED_BY]->(r:Account)
WHERE t.fraud_status = 'FRAUD'
WITH
    r,
    count(DISTINCT s) AS unique_senders,
    count(t) AS fraud_transactions,
    sum(t.amount) AS total_fraud_amount
RETURN
    r.id AS fraud_hub,
    unique_senders,
    fraud_transactions,
    round(total_fraud_amount, 2) AS total_fraud_amount
ORDER BY total_fraud_amount DESC
LIMIT 10;