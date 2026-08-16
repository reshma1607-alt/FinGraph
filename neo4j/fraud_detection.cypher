// ==========================================
// FinGraph Fraud Detection Queries
// ==========================================


// 1. SMURFING DETECTION
// Detect accounts sending transactions
// between $9,000 and $10,000

MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver:Account)
WHERE t.amount >= 9000 AND t.amount <= 10000
RETURN sender.id AS sender,
       t.amount AS amount,
       receiver.id AS receiver,
       t.transaction_id AS transaction_id
ORDER BY amount DESC;


// 2. STARBURST DETECTION
// Detect accounts receiving transactions
// from many different accounts

MATCH (sender:Account)-[t:TRANSFERRED_TO]->(receiver:Account)
WITH receiver,
     count(DISTINCT sender) AS sender_count,
     sum(t.amount) AS total_received
WHERE sender_count >= 10
RETURN receiver.id AS suspicious_account,
       sender_count,
       total_received
ORDER BY sender_count DESC;


// 3. CIRCULAR MONEY FLOW DETECTION
// Detect A -> B -> C -> A

MATCH (a:Account)-[:TRANSFERRED_TO]->(b:Account)
      -[:TRANSFERRED_TO]->(c:Account)
      -[:TRANSFERRED_TO]->(a)

RETURN a.id AS account_a,
       b.id AS account_b,
       c.id AS account_c;


// 4. ACCOUNT RISK SCORE

MATCH (a:Account)

OPTIONAL MATCH (a)-[out:TRANSFERRED_TO]->()
WITH a, count(out) AS outgoing_transactions

OPTIONAL MATCH (a)<-[inc:TRANSFERRED_TO]-()
WITH a,
     outgoing_transactions,
     count(inc) AS incoming_transactions

RETURN a.id AS account,
       outgoing_transactions,
       incoming_transactions,
       (outgoing_transactions * 2 +
        incoming_transactions) AS risk_score

ORDER BY risk_score DESC
LIMIT 20;