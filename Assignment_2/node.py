# node.py
"""
Byzantine Agreement Node Server using XML-RPC.
Supports Commander and Lieutenants with Byzantine fault simulation.
"""

from xmlrpc.server import SimpleXMLRPCServer
import sys
import threading
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
    datefmt= "%d/%m/%Y %H:%M:%S",
    # Added handlers list to include both the file and console stream
    handlers=[
        logging.FileHandler("console.log", mode='a'), # Use 'a' for append
        logging.StreamHandler(sys.stdout)
    ]
)

shutdown_flag = threading.Event()

class Node:
    def __init__(self, node_id, is_byzantine=False):
        self.node_id = node_id
        self.is_byzantine = is_byzantine
        self.received_orders = {}

    def receive_order(self, sender_id, order):
        logging.info(f"[Node {self.node_id}] Received '{order}' from {sender_id}") 
        if self.is_byzantine:
            order = "RETREAT" if order == "ATTACK" else "ATTACK"
            logging.info(f"[Node {self.node_id}] Byzantine behavior: flipped to '{order}'") 
        self.received_orders[sender_id] = order
        return True

    def get_order_from(self, sender_id):
        return self.received_orders.get(sender_id, "UNKNOWN")

    def decide_order(self):
        votes = list(self.received_orders.values())
        decision = max(set(votes), key=votes.count)
        logging.info(f"[Node {self.node_id}] Final decision: {decision}") 
        return decision

    def shutdown(self):
        logging.info(f"[Node {self.node_id}] Shutting down...") 
        shutdown_flag.set()
        return True

def run_server(node_id, port, is_byzantine=False):
    node = Node(node_id, is_byzantine)
    server = SimpleXMLRPCServer(("localhost", port), allow_none=True, logRequests=False) 
    server.register_instance(node)
    logging.info(f"[Node {node_id}] Started on port {port} (Byzantine: {is_byzantine})") 

    while not shutdown_flag.is_set():
        server.handle_request()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python node.py <NodeName> <Port> [byzantine]")
        sys.exit(1)

    name = sys.argv[1]
    port = int(sys.argv[2])
    is_byzantine = len(sys.argv) == 4 and sys.argv[3].lower() == "byzantine"

    run_server(name, port, is_byzantine)