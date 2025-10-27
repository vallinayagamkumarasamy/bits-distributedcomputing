"""
# Usage: python3 run_simulation.py
# This script simulates Lamport's Mutual Exclusion Algorithm
# - Launches multiple node processes that compete for critical section access
# - Uses Lamport timestamps for ordering requests
# - Verifies mutual exclusion and message correctness
# - Generates detailed logs in console.log
#Lamport's Mutual Exclusion Simulation Runner
Launches all nodes and coordinator
"""

import multiprocessing
import subprocess
import logging
import time
import sys
import os

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("console.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

BASE_PORT = 8000

def launch_node(node_id, total_nodes, base_port, request_delay):
    """Launch a single node process"""
    logging.info(f"Launching Node-{node_id}")
    subprocess.run([
        "python3", "lamport_node.py",
        str(node_id),
        str(total_nodes),
        str(base_port),
        str(request_delay)
    ])

def launch_coordinator(total_nodes, base_port):
    """Launch coordinator process"""
    time.sleep(2)  # Wait for nodes to start
    logging.info("Launching Coordinator")
    subprocess.run([
        "python3", "coordinator.py",
        str(total_nodes),
        str(base_port)
    ])

if __name__ == "__main__":
    print("\n" + "="*60)
    print("    LAMPORT'S MUTUAL EXCLUSION SIMULATION Using RPC")
    print("    WORKS ON LINUX AND MAC TERMINALS ONLY")
    print("="*60)
    print("\nWhat this script does:")
    print("1. Launches nodes based on user input")
    print("2. Each node enters and exits critical section ONCE")
    print("3. During CS: performs 3 arithmetic operations and logs results")
    print("4. Uses Lamport timestamps for message ordering")
    print("5. Coordinator waits, collects statistics, and verifies mutual exclusion")
    print("6. Script completes after all nodes finish their single CS cycle")
    print("7. Generates logs and evidence files for analysis")
    print("="*60 + "\n")
    
    # Clear previous log
    if os.path.exists("console.log"):
        os.remove("console.log")
    
    # Clear any existing evidence files
    for file in os.listdir("."):
        if file.startswith("cs_evidence_node_") and file.endswith(".txt"):
            os.remove(file)
            
    # Get number of nodes
    try:
        num_nodes = int(input("Enter number of nodes: "))
    except ValueError:
        print("Invalid input. Please enter an integer.")
        sys.exit(1)
    
    if num_nodes < 2:
        print("Error: Number of nodes must be at least 2")
        sys.exit(1)
    
    # Staggered delays to avoid simultaneous requests
    base_delays = [3.0, 4.0, 2.0, 3.5, 4.5, 2.5, 3.8, 4.2, 2.8, 3.2]
    
    processes = []
    
    # Launch all node processes
    for node_id in range(1, num_nodes + 1):
        delay = base_delays[(node_id - 1) % len(base_delays)]
        p = multiprocessing.Process(
            target=launch_node,
            args=(node_id, num_nodes, BASE_PORT, delay),
            name=f"Node-{node_id}"
        )
        processes.append(p)
        p.start()
        time.sleep(0.3)
    
    # Launch coordinator
    coordinator_process = multiprocessing.Process(
        target=launch_coordinator,
        args=(num_nodes, BASE_PORT),
        name="Coordinator"
    )
    coordinator_process.start()
    
    # Wait for all processes
    for p in processes:
        p.join()
    coordinator_process.join()
    
    logging.info("Simulation complete.")
    print("\n" + "="*80)
    print("==== Simulation complete. All processes finished. ====")
    print("==== Check 'console.log' for full output. ====")
    print("="*80 + "\n")
    
    sys.exit(0)