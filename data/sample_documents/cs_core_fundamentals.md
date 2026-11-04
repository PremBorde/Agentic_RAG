# Computer Science Fundamentals & Core Engineering Reference

## Graph Algorithms and Network Routing

### Dijkstra's Algorithm
Dijkstra's algorithm is a greedy graph search algorithm that solves the single-source shortest path problem for a directed or undirected graph with non-negative edge weights. It maintains a set of visited vertices and repeatedly selects the unvisited vertex with the minimum tentative distance from the source vertex. The algorithm uses a priority queue (min-heap) to achieve an optimal time complexity of O((V + E) log V), where V is the number of vertices and E is the number of edges.

### Bellman-Ford Algorithm
The Bellman-Ford algorithm computes shortest paths from a single source vertex to all other vertices in a weighted digraph. Unlike Dijkstra's algorithm, Bellman-Ford can handle graphs in which some edge weights are negative numbers. It runs in O(V * E) time by relaxing all edges V - 1 times. Furthermore, Bellman-Ford can detect negative-weight cycles: if an edge can still be relaxed after V - 1 iterations, a negative cycle exists.

---

## Database Management Systems (DBMS)

### Database Normalization (1NF, 2NF, 3NF, BCNF)
Database normalization is the process of organizing structured data in a relational database to reduce data redundancy and eliminate anomalies (insertion, update, and deletion anomalies).
- First Normal Form (1NF): Each column must contain atomic (indivisible) values, and each record must be unique with a primary key.
- Second Normal Form (2NF): Must be in 1NF, and all non-key attributes must be fully functionally dependent on the entire primary key (no partial functional dependencies).
- Third Normal Form (3NF): Must be in 2NF, and no non-key attribute may be transitively dependent on the primary key (no transitive dependencies).
- Boyce-Codd Normal Form (BCNF): A stricter version of 3NF where for every functional dependency X -> Y, X must be a super key.

### ACID Properties in Relational Transactions
- Atomicity: Guarantees that all operations within a transaction complete successfully, or all changes are rolled back completely.
- Consistency: Ensures that any transaction will bring the database from one valid state to another, maintaining all schema constraints and foreign keys.
- Isolation: Ensures that concurrent execution of transactions leaves the database in the same state as if transactions were executed sequentially.
- Durability: Guarantees that once a transaction has been committed, it will remain committed even in the event of a system crash or power outage.

---

## Operating Systems & Concurrency

### Deadlock and Coffman Conditions
In concurrent computing, a deadlock is a state in which each member of a group of processes is waiting for another member, including itself, to take action, such as sending a message or releasing a lock.
A deadlock can occur if and only if all four Coffman conditions hold simultaneously:
1. Mutual Exclusion: At least one resource must be held in a non-shareable mode.
2. Hold and Wait: A process must concurrently hold at least one resource and request additional resources that are being held by other processes.
3. No Preemption: Resources cannot be forcibly confiscated from a process; they can only be released voluntarily by the holding process.
4. Circular Wait: A closed chain of processes exists such that each process holds at least one resource needed by the next process in the chain.

### Deadlock Avoidance: Banker's Algorithm
Dijkstra's Banker's Algorithm is a deadlock avoidance algorithm that tests for safety by simulating the allocation of predetermined maximum possible amounts of all resources, and then makes an s-state check to test for possible activities, before deciding whether allocation should be allowed to continue.

