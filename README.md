# Distributed Computing Assignments

This repository contains Lamport Distributed mutual exclusion using RPC and Byzantine Agreement protocol using RPC script.s

- Assignment_1/
  - coordinator.py
  - lamport_node.py
  - run_simulation.py
 
- Assignment_2/
  - commander.py
  - node.py
  - run_simulation.py

## Overview

Assignment_1 implements a Lamport-style mutual exclusion / coordinator simulation. Nodes communicate (simulated) and request access to a critical section using Lamport logical clocks. The simulation produces per-node evidence files (`cs_evidence_node_*.txt`) that show when each node entered the critical section (useful to verify mutual exclusion and ordering) and `console.log` contains the full execution details.

Assignment_2 implements a simplified version of the Byzantine Generals / consensus (commander and nodes) exercise. The code demonstrates how a commander sends orders and how nodes exchange/decide on values, highlighting agreement and fault-tolerance concepts used in distributed consensus problems. check `console.log` for full execution flow.

## Files and purpose

Assignment_1/
- `lamport_node.py` — Node implementation using Lamport timestamps and message handling logic for mutual exclusion.
- `coordinator.py` — (If present) coordinates requests or simulates a central coordinator mechanism used in the assignment.
- `run_simulation.py` — Script that starts the simulation for Assignment 1, creates multiple node instances (or processes/threads), and drives the simulated message exchange. Running this will typically create or update the `cs_evidence_node_*.txt` files.
- `cs_evidence_node_*.txt` — Output evidence files showing critical-section entry events for each node. Use these files to verify that only one node is in the critical section at any time and to inspect Lamport ordering.
- `console.log` — Full terminal output will also be logged in console.log file

Assignment_2/
- `commander.py` — The commander process that sends orders to nodes (may simulate faulty or correct behavior depending on parameters).
- `node.py` — Node logic to receive commands, exchange messages, and reach a decision (implements the node-side of the consensus algorithm taught in the class).
- `run_simulation.py` — Script that runs the assignment 2 scenario, starts the commander and nodes, and prints or logs the final decisions reached by nodes.
- `console.log` — Full terminal output will also be logged in console.log file
