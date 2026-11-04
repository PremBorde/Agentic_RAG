"""
Generates a comprehensive 205-query benchmark dataset for Advanced RAG Evaluation.
Categories covered:
1. Exact Keyword (35 queries)
2. Acronym & Identifier (30 queries)
3. Semantic & Conceptual (45 queries)
4. Contextual Follow-up (30 queries)
5. Multi-Document (30 queries)
6. Out-of-Corpus / Negative Queries (35 queries)

Total: 205 labelled queries with verified chunk IDs and expected keywords.
"""

import os
import json

queries = []

def add_q(qid, text, cat, docs, cids, keywords):
    queries.append({
        "id": f"q_{qid:03d}",
        "query": text,
        "category": cat,
        "relevant_doc_names": docs,
        "relevant_chunk_ids": cids,
        "expected_keywords": keywords
    })

c = 1

# ── 1. EXACT KEYWORD QUERIES (35) ───────────────────────────────────────────
keywords_data = [
    ("DAA-1", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa-1", "fibonacci", "recursive"]),
    ("DAA-2", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa-2", "job sequencing", "deadlines", "greedy"]),
    ("DAA-3", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa-3", "huffman encoding", "greedy"]),
    ("DAA-4", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa-4", "fractional knapsack", "greedy"]),
    ("DAA-5", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa-5", "0-1 knapsack", "dynamic programming"]),
    ("ML-1", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1", "file-1-1793441378-c2"], ["ml-1", "customer churn", "classifier"]),
    ("ML-2", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["ml-2", "emails", "spam", "knn", "svm"]),
    ("ML-3", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["ml-3", "diabetes.csv", "knn", "confusion matrix"]),
    ("ML-4", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["ml-4", "k-means", "sales_data_sample.csv", "elbow method"]),
    ("ML-5", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["ml-5", "gradient descent", "local minima", "y = (x+3)"]),
    ("BC-1", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["bc-1", "metamask", "ether"]),
    ("BC-2", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["bc-2", "wallet", "metamask"]),
    ("BC-3", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["bc-3", "smart contract", "bank account"]),
    ("BC-4", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["bc-4", "survey report", "blockchains"]),
    ("BC-5", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["bc-5", "hyperledger", "business network"]),
    ("1NF", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["1nf", "first normal form", "atomic"]),
    ("2NF", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["2nf", "second normal form", "partial functional"]),
    ("3NF", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["3nf", "third normal form", "transitive"]),
    ("BCNF", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["bcnf", "boyce-codd", "super key"]),
    ("ACID", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5", "note-2-1793706942-c6"], ["acid", "atomicity", "consistency", "isolation", "durability"]),
    ("Coffman conditions", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7", "note-2-1793706942-c8"], ["coffman", "mutual exclusion", "hold and wait", "circular wait"]),
    ("Banker's Algorithm", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["banker's", "deadlock avoidance", "safety"]),
    ("emails.csv", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["emails.csv", "spam", "kaggle"]),
    ("diabetes.csv", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["diabetes.csv", "knn", "accuracy"]),
    ("sales_data_sample.csv", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["sales_data_sample.csv", "k-means"]),
    ("y = (x+3)^2", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["gradient descent", "local minima", "x = 2"]),
    ("Hyperledger", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["hyperledger", "business network"]),
    ("Metamask", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "ether", "wallet"]),
    ("O((V + E) log V)", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["o((v + e) log v)", "dijkstra", "priority queue"]),
    ("O(V * E)", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2", "note-2-1793706942-c3"], ["o(v * e)", "bellman-ford", "relaxing"]),
    ("min-heap", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["min-heap", "priority queue", "dijkstra"]),
    ("Fibonacci numbers", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["fibonacci", "recursive", "non-recursive"]),
    ("Huffman Encoding", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["huffman encoding", "greedy strategy"]),
    ("Job sequencing with deadlines", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["job sequencing", "deadlines", "greedy"]),
    ("Circular Wait", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c8"], ["circular wait", "coffman", "closed chain"])
]

for kw, docs, cids, expected in keywords_data:
    add_q(c, kw, "exact_keyword", docs, cids, expected)
    c += 1

# ── 2. ACRONYM & IDENTIFIER QUERIES (30) ────────────────────────────────────
acronyms_data = [
    ("What is SVM in machine learning practicals?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["svm", "support vector machine", "ml-2"]),
    ("Which assignment uses KNN algorithm?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["knn", "k-nearest neighbors", "ml-2", "ml-3"]),
    ("Explain DBMS normalization forms", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c3", "note-2-1793706942-c4"], ["dbms", "normalization", "relational"]),
    ("What is BCNF and how does it relate to 3NF?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4", "note-2-1793706942-c5"], ["bcnf", "3nf", "super key"]),
    ("What does 1NF require?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["1nf", "atomic", "primary key"]),
    ("What does 2NF eliminate?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["2nf", "partial functional dependencies"]),
    ("What does 3NF eliminate?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["3nf", "transitive dependencies"]),
    ("Define ACID atomicity", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["atomicity", "rollback", "transaction"]),
    ("Define ACID consistency", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["consistency", "schema constraints"]),
    ("Define ACID isolation", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6"], ["isolation", "concurrent"]),
    ("Define ACID durability", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6"], ["durability", "committed", "crash"]),
    ("What is DAA Group A about?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["daa", "group a", "design and analysis of algorithms"]),
    ("What is Group B Machine Learning?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1", "file-1-1793441378-c2"], ["group b", "machine learning"]),
    ("What is Group C Blockchain?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["group c", "blockchain technology"]),
    ("What does ML-1 churn dataset have?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["ml-1", "kaggle", "10,000 samples", "14 features"]),
    ("CreditScore and Geography in ML-1", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["creditscore", "geography", "customerid"]),
    ("What is the confusion matrix in ML-3?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["confusion matrix", "accuracy", "error rate", "precision", "recall"]),
    ("Elbow method in ML-4", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["elbow method", "k-means", "clusters"]),
    ("Gradient descent local minima formula", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["gradient descent", "local minima", "y = (x+3)"]),
    ("Metamask wallet in BC-2", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "wallet", "crypto transactions"]),
    ("Solidity deposit withdraw in BC-3", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["deposit money", "withdraw money", "show balance"]),
    ("Survey report on blockchains BC-4", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["survey report", "types of blockchains"]),
    ("Hyperledger network in BC-5", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["hyperledger", "business network"]),
    ("Shortest path algorithm with non-negative weights", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1"], ["dijkstra", "non-negative", "shortest path"]),
    ("Shortest path with negative edge weights", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2"], ["bellman-ford", "negative numbers"]),
    ("Detect negative weight cycle", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c3"], ["bellman-ford", "negative-weight cycles"]),
    ("Deadlock hold and wait condition", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7", "note-2-1793706942-c8"], ["hold and wait", "resource"]),
    ("Deadlock no preemption condition", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c8"], ["no preemption", "voluntarily"]),
    ("Deadlock mutual exclusion condition", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7"], ["mutual exclusion", "non-shareable"]),
    ("Banker's Algorithm safety simulation", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["banker's algorithm", "safety", "s-state check"])
]

for q, docs, cids, expected in acronyms_data:
    add_q(c, q, "acronym", docs, cids, expected)
    c += 1

# ── 3. SEMANTIC & CONCEPTUAL QUERIES (45) ───────────────────────────────────
semantic_data = [
    ("How does greedy choice property solve fractional knapsack?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["fractional knapsack", "greedy"]),
    ("Explain the difference between recursive and non-recursive Fibonacci", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["fibonacci", "non-recursive", "recursive", "time and space"]),
    ("How are deadlines scheduled in job sequencing?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["job sequencing", "deadlines", "greedy"]),
    ("What data compression method uses a greedy tree in DAA?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["huffman encoding", "greedy"]),
    ("Why is dynamic programming used for 0/1 knapsack instead of greedy?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["0-1 knapsack", "dynamic programming", "branch and bound"]),
    ("How is customer churn modeled with a neural network?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1", "file-1-1793441378-c2"], ["customer churn", "neural network", "classifier"]),
    ("What are the steps to preprocess bank customer churn data?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["normalize", "training and test", "feature and target"]),
    ("How to compare KNN and SVM for spam classification?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["knn", "svm", "spam", "analyze their performance"]),
    ("What evaluation metrics are computed on the diabetes dataset?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["confusion matrix", "accuracy", "error rate", "precision", "recall"]),
    ("How does the elbow method determine optimal k in clustering?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["elbow method", "number of clusters", "k-means"]),
    ("Find the local minima of a convex function using gradient steps", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["gradient descent", "local minima", "y = (x+3)"]),
    ("How does a crypto user spend Ether in Metamask?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "spending ether"]),
    ("How to create a test network smart contract for banking?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["smart contract", "bank account", "deposit", "withdraw"]),
    ("What are real-time applications of enterprise blockchains?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["types of blockchains", "real-time use cases"]),
    ("How to build permissioned business networks using Hyperledger?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["business network", "hyperledger"]),
    ("Why does Dijkstra require edge weights to be non-negative?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1"], ["dijkstra", "non-negative"]),
    ("How does Dijkstra maintain tentative shortest distances?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1"], ["tentative distance", "visited vertices", "min-heap"]),
    ("Explain edge relaxation in the Bellman-Ford algorithm", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2"], ["relaxing all edges", "v - 1", "bellman-ford"]),
    ("Why can Bellman-Ford find negative weight cycles?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c3"], ["negative-weight cycles", "relaxed after v - 1"]),
    ("Explain how functional dependencies determine normal forms", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4", "note-2-1793706942-c5"], ["functional dependency", "normal form", "primary key"]),
    ("Why are partial dependencies prohibited in 2NF?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["partial functional dependencies", "2nf"]),
    ("How does 3NF eliminate transitive functional dependencies?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["transitive dependencies", "3nf"]),
    ("What makes BCNF stricter than standard third normal form?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["bcnf", "stricter", "super key"]),
    ("How does database transaction rollback maintain atomicity?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["atomicity", "rolled back completely"]),
    ("How does consistency enforce relational integrity constraints?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["consistency", "valid state", "schema constraints"]),
    ("Why does isolation require concurrent transactions to mirror serial execution?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6"], ["isolation", "concurrent execution", "sequentially"]),
    ("How does durability protect data during unexpected power failures?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6"], ["durability", "committed", "power outage"]),
    ("What causes a concurrent process group to enter deadlock?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7"], ["deadlock", "waiting for another member", "releasing a lock"]),
    ("How does circular wait form a closed dependency chain?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c8"], ["circular wait", "closed chain of processes"]),
    ("How does Banker's algorithm test for safe state allocation?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["banker's algorithm", "safe", "s-state check", "maximum possible"]),
    ("Hinglish: Knapsack problem greedy se kaise solve karte hai?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["fractional knapsack", "greedy"]),
    ("Hinglish: Fibonacci non-recursive program ka practical DAA-1", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["fibonacci", "daa-1"]),
    ("Hinglish: Customer churn neural network model training steps", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["customer churn", "normalize", "accuracy score"]),
    ("Hinglish: Email spam binary classification KNN and SVM", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["spam", "knn", "svm"]),
    ("Hinglish: Metamask wallet create karke Ether spend kaise kare?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "wallet", "ether"]),
    ("Hinglish: Smart contract me deposit withdraw balance ka assignment", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["deposit money", "withdraw money", "show balance"]),
    ("Hinglish: Hyperledger me business network kaise banaye?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["hyperledger", "business network"]),
    ("Hinglish: Dijkstra shortest path algorithm ka time complexity kya hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["dijkstra", "o((v + e) log v)"]),
    ("Hinglish: Bellman-Ford negative edge weights ko kaise handle karta hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2", "note-2-1793706942-c3"], ["bellman-ford", "negative"]),
    ("Hinglish: Database normalization me 1NF 2NF 3NF kya hote hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["normalization", "1nf", "2nf", "3nf"]),
    ("Hinglish: BCNF aur 3NF me kya difference hota hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4", "note-2-1793706942-c5"], ["bcnf", "3nf", "super key"]),
    ("Hinglish: Database ACID properties ka meaning kya hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5", "note-2-1793706942-c6"], ["acid", "atomicity", "consistency"]),
    ("Hinglish: Operating system me deadlock ke char conditions kaun se hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7", "note-2-1793706942-c8"], ["deadlock", "coffman"]),
    ("Hinglish: Banker's algorithm deadlock avoid kaise karta hai?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["banker's algorithm", "safety"]),
    ("Hinglish: Diabetes dataset par confusion matrix kaise calculate kare?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["diabetes", "confusion matrix", "accuracy"])
]

for q, docs, cids, expected in semantic_data:
    add_q(c, q, "semantic", docs, cids, expected)
    c += 1

# ── 4. CONTEXTUAL FOLLOW-UP QUERIES (30) ────────────────────────────────────
followups_data = [
    ("What is its time complexity?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2"], ["o((v + e) log v)", "time complexity"]),
    ("How does it handle negative weights?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2"], ["bellman-ford", "negative numbers"]),
    ("Which dataset does it use?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["dataset", "kaggle", "samples"]),
    ("Explain step 3 of the process", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["normalize", "train and test data"]),
    ("What are the 4 conditions required for it to occur?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7", "note-2-1793706942-c8"], ["coffman conditions", "mutual exclusion", "hold and wait"]),
    ("How is the optimal number of clusters determined in it?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["elbow method", "clusters"]),
    ("What operations can a customer perform on it?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["deposit money", "withdraw money", "show balance"]),
    ("Which network is used for deploying it?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["test network", "smart contract"]),
    ("How does it simulate safe state allocation?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["safety", "banker's algorithm", "s-state"]),
    ("What anomalies does this eliminate?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c3"], ["insertion", "update", "deletion anomalies"]),
    ("Why must non-key attributes be fully dependent on it?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["2nf", "functional dependent", "primary key"]),
    ("Why are transitive dependencies disallowed in this form?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["3nf", "transitive dependent"]),
    ("What is the super key requirement for X in this form?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["bcnf", "super key", "functional dependency"]),
    ("What happens if a failure occurs during execution?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5"], ["atomicity", "rolled back"]),
    ("How does it guarantee durability after a crash?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6"], ["durability", "committed", "system crash"]),
    ("What starting value of x is used for it?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c3"], ["starting from x = 2", "local minima"]),
    ("Which two classification models are compared in it?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["knn", "svm", "k-nearest neighbors"]),
    ("What features are included in the Kaggle churn dataset?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["customerid", "creditscore", "geography", "gender"]),
    ("How many samples does the churn dataset contain?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["10,000 samples", "14 features"]),
    ("How many points are assigned for the accuracy score?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["accuracy score", "5 points"]),
    ("How many iterations does Bellman-Ford run?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2", "note-2-1793706942-c3"], ["v - 1 times", "iterations"]),
    ("Which data structure optimizes Dijkstra search?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["priority queue", "min-heap"]),
    ("What strategy does job sequencing use?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["greedy method", "job sequencing"]),
    ("What strategy does Huffman encoding use?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["greedy strategy", "huffman"]),
    ("What strategies can be used for 0-1 knapsack?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["dynamic programming", "branch and bound"]),
    ("Which wallet is installed for crypto transactions?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "crypto transactions"]),
    ("Which framework is used for building the business network?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["hyperledger", "business network"]),
    ("What resource property makes it non-shareable in Coffman?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7"], ["mutual exclusion", "non-shareable"]),
    ("How can resources be released under the third condition?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c8"], ["no preemption", "voluntarily"]),
    ("What check is performed in Banker's algorithm?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c9"], ["s-state check", "test for possible activities"])
]

for q, docs, cids, expected in followups_data:
    add_q(c, q, "follow_up", docs, cids, expected)
    c += 1

# ── 5. MULTI-DOCUMENT QUERIES (30) ──────────────────────────────────────────
multidoc_data = [
    ("Compare greedy methods in fractional knapsack with Dijkstra shortest path", ["LP-III practical detail list.pdf", "Computer Science Fundamentals & Core Engineering"], ["file-1-1793441378-c1", "note-2-1793706942-c1"], ["greedy", "fractional knapsack", "dijkstra"]),
    ("Compare dynamic programming in 0/1 knapsack with Bellman-Ford edge relaxation", ["LP-III practical detail list.pdf", "Computer Science Fundamentals & Core Engineering"], ["file-1-1793441378-c1", "note-2-1793706942-c2"], ["dynamic programming", "0-1 knapsack", "bellman-ford"]),
    ("How do blockchain transactions differ from relational database ACID transactions?", ["LP-III practical detail list.pdf", "Computer Science Fundamentals & Core Engineering"], ["file-1-1793441378-c4", "note-2-1793706942-c5"], ["blockchain", "acid", "smart contract", "transactions"]),
    ("Compare Dijkstra's shortest path algorithm with Dijkstra's Banker's algorithm", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c9"], ["dijkstra", "shortest path", "banker's algorithm"]),
    ("Which topics in algorithms use priority queues or heaps?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["priority queue", "min-heap", "dijkstra"]),
    ("Compare customer churn neural network with SVM spam classification", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["churn", "neural network", "svm", "spam"]),
    ("What clustering and classification algorithms are present in the practicals?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["knn", "svm", "k-means", "neural network"]),
    ("Compare greedy job sequencing with fractional knapsack in DAA", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1"], ["job sequencing", "fractional knapsack", "greedy"]),
    ("How do Metamask wallet operations compare to bank account operations in BC-3?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "wallet", "smart contract", "bank account"]),
    ("What graph algorithms are detailed in the computer science fundamentals?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["dijkstra", "bellman-ford", "shortest path"]),
    ("Compare single-source shortest path algorithms: Dijkstra vs Bellman-Ford", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c1", "note-2-1793706942-c2"], ["dijkstra", "bellman-ford", "non-negative", "negative numbers"]),
    ("What normal forms address partial and transitive dependencies?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4"], ["2nf", "3nf", "partial", "transitive"]),
    ("Compare 3NF and BCNF requirements for functional dependencies", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c4", "note-2-1793706942-c5"], ["3nf", "bcnf", "super key"]),
    ("Which properties ensure transactional safety and concurrency control in DBMS?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5", "note-2-1793706942-c6"], ["acid", "atomicity", "consistency", "isolation", "durability"]),
    ("How do deadlock conditions compare with deadlock avoidance using Banker's?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c7", "note-2-1793706942-c9"], ["coffman", "banker's algorithm", "deadlock avoidance"]),
    ("What datasets are used across all machine learning practicals?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["bank customer churn", "emails.csv", "diabetes.csv", "sales_data_sample.csv"]),
    ("Compare Kaggle churn dataset features with diabetes dataset features", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["churn", "creditscore", "diabetes", "dataset"]),
    ("What optimization methods are used: Gradient Descent vs Dynamic Programming?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1", "file-1-1793441378-c3"], ["gradient descent", "dynamic programming", "0-1 knapsack"]),
    ("Compare supervised classification and unsupervised clustering assignments", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["classification", "k-means", "knn", "clustering"]),
    ("What platforms are used for blockchain assignments: Metamask vs Hyperledger?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c4"], ["metamask", "hyperledger", "blockchain"]),
    ("How does smart contract state balance compare to ACID durability?", ["LP-III practical detail list.pdf", "Computer Science Fundamentals & Core Engineering"], ["file-1-1793441378-c4", "note-2-1793706942-c6"], ["smart contract", "balance", "durability", "committed"]),
    ("Compare negative cycle detection with circular wait in operating systems", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c3", "note-2-1793706942-c8"], ["negative cycle", "circular wait", "closed chain"]),
    ("How are time complexities expressed for Dijkstra and Bellman-Ford?", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c2"], ["o((v + e) log v)", "o(v * e)"]),
    ("What assignments in LP-3 involve Kaggle dataset links?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["kaggle", "churn", "emails.csv", "diabetes.csv"]),
    ("Which assignments require computing a confusion matrix?", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2", "file-1-1793441378-c3"], ["confusion matrix", "ml-1", "ml-3"]),
    ("Compare binary classification of emails with customer churn prediction", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c2"], ["binary classification", "churn", "leave or not"]),
    ("Which algorithms use greedy strategies in algorithms and graphs?", ["LP-III practical detail list.pdf", "Computer Science Fundamentals & Core Engineering"], ["file-1-1793441378-c1", "note-2-1793706942-c1"], ["greedy", "knapsack", "dijkstra", "huffman"]),
    ("Compare resource preemption in deadlocks with transaction rollback in ACID", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c5", "note-2-1793706942-c8"], ["no preemption", "atomicity", "rollback"]),
    ("Compare isolation in databases with mutual exclusion in OS concurrency", ["Computer Science Fundamentals & Core Engineering"], ["note-2-1793706942-c6", "note-2-1793706942-c7"], ["isolation", "mutual exclusion", "concurrent"]),
    ("Summarize all practical assignments under Group A, B, and C", ["LP-III practical detail list.pdf"], ["file-1-1793441378-c1", "file-1-1793441378-c4"], ["group a", "group b", "group c", "daa", "ml", "bc"])
]

for q, docs, cids, expected in multidoc_data:
    add_q(c, q, "multi_document", docs, cids, expected)
    c += 1

# ── 6. OUT-OF-CORPUS / NEGATIVE QUERIES (35) ────────────────────────────────
negative_data = [
    "What is quantum key distribution in cryptography?",
    "Explain photosynthesis light reactions in C3 and C4 plants",
    "Who was the first emperor of the Roman Empire?",
    "How do React Server Components work in Next.js 15?",
    "Explain Docker swarm overlay networking configuration",
    "What is the current stock price of Tesla on NASDAQ?",
    "What is the capital city of Australia?",
    "How does mRNA vaccine delivery work in human cells?",
    "Explain the causes and timeline of the French Revolution",
    "How to configure Kubernetes ingress controller with Let's Encrypt TLS?",
    "What is the chemical composition of volcanic basalt rock?",
    "Explain the rules of cricket and the lbw dismissal criteria",
    "Who wrote the novel Crime and Punishment?",
    "What are the thermodynamic laws governing black hole radiation?",
    "How does CRISPR-Cas9 perform targeted gene editing?",
    "What is the recipe and temperature for baking French sourdough bread?",
    "Explain the difference between Keynesian and Austrian economics",
    "What is the highest mountain peak in South America?",
    "How do transformer multi-head attention weights get calculated in GPT-4?",
    "What is the function of mitochondria in eukaryotic cellular respiration?",
    "How to tune guitar strings to open D tuning?",
    "What caused the collapse of the Bronze Age civilizations in 1200 BCE?",
    "How do airplanes generate lift using Bernoulli's principle and airfoil camber?",
    "Explain the difference between supervised fine-tuning and RLHF in LLMs",
    "What is the legal difference between common law and civil law systems?",
    "How to implement a Red-Black tree self-balancing rotation in Rust?",
    "What is the atomic mass and electron configuration of Titanium?",
    "Explain the plot summary of Shakespeare's Macbeth",
    "What are the symptoms and treatments of acute Lyme disease?",
    "How does a four-stroke internal combustion engine work?",
    "What is the monetary policy function of the Federal Reserve in controlling inflation?",
    "How to brew specialty pour-over coffee with a V60 dripper?",
    "What is dark matter and how do astronomers infer its gravitational presence?",
    "Explain the architectural difference between RISC-V and ARM instruction sets",
    "How does optical fiber transmit light through total internal reflection?"
]

for neg_q in negative_data:
    add_q(c, neg_q, "out_of_corpus", [], [], [])
    c += 1

print(f"Total queries generated: {len(queries)}")

# Write to file
target_path = os.path.join(os.path.dirname(__file__), "rag_benchmark_200.json")
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(queries, f, indent=2, ensure_ascii=False)

print(f"Successfully saved 205 benchmark queries to {target_path}")

