# commander.py
import xmlrpc.client
import time
import sys
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

def build_lieutenant_nodes(count):
    return {f"Lieutenant-{i+1}": {"port": 8001 + i} for i in range(count)}

def send_order(order, nodes):
    for name, config in nodes.items():
        proxy = xmlrpc.client.ServerProxy(f"http://localhost:{config['port']}/", allow_none=True)
        proxy.receive_order("Commander", order)
        logging.info(f"Sent '{order}' to {name}") 

def forward_orders(nodes):
    for sender_name, sender_config in nodes.items():
        sender_proxy = xmlrpc.client.ServerProxy(f"http://localhost:{sender_config['port']}/", allow_none=True)
        commander_order = sender_proxy.get_order_from("Commander")
        for receiver_name, receiver_config in nodes.items():
            if receiver_name != sender_name:
                receiver_proxy = xmlrpc.client.ServerProxy(f"http://localhost:{receiver_config['port']}/", allow_none=True)
                receiver_proxy.receive_order(sender_name, commander_order)
                logging.info(f"{sender_name} forwarded '{commander_order}' to {receiver_name}")

def collect_decisions(nodes):
    decisions = {}
    for name, config in nodes.items():
        proxy = xmlrpc.client.ServerProxy(f"http://localhost:{config['port']}/", allow_none=True)
        decision = proxy.decide_order()
        decisions[name] = decision
    
    # Analyze majority decision
    decision_votes = list(decisions.values())
    if decision_votes:
        # Count votes for each decision
        vote_count = {}
        for vote in decision_votes:
            vote_count[vote] = vote_count.get(vote, 0) + 1
        
        # Find majority decision
        majority_decision = max(vote_count.keys(), key=lambda x: vote_count[x])
        majority_count = vote_count[majority_decision]
        total_nodes = len(decision_votes)
        
        logging.info(f"\n=== BYZANTINE AGREEMENT FINAL RESULT ===")
        logging.info(f"Individual decisions: {decisions}")
        logging.info(f"Vote count: {vote_count}")
        logging.info(f"Majority decision: {majority_decision} ({majority_count}/{total_nodes} nodes)")
        logging.info(f"Consensus achieved: {'YES' if majority_count > total_nodes/2 else 'NO'}")
        logging.info(f"==========================================")
        
        print(f"\n=== BYZANTINE AGREEMENT FINAL RESULT ===")
        print(f"Individual decisions: {decisions}")
        print(f"Vote count: {vote_count}")
        print(f"Majority decision: {majority_decision} ({majority_count}/{total_nodes} nodes)")
        print(f"Consensus achieved: {'YES' if majority_count > total_nodes/2 else 'NO'}")
        print(f"==========================================\n")
    
    return decisions

def shutdown_nodes(nodes):
    for name, config in nodes.items():
        proxy = xmlrpc.client.ServerProxy(f"http://localhost:{config['port']}/", allow_none=True)
        try:
            proxy.shutdown()
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python commander.py <NumberOfLieutenants> <Order>") 
        sys.exit(1)

    count = int(sys.argv[1])
    order = sys.argv[2].upper()
    NODES = build_lieutenant_nodes(count)

    logging.info(f"Commander initiating order: {order}") 
    send_order(order, NODES)
    time.sleep(1)
    forward_orders(NODES)
    time.sleep(1)
    collect_decisions(NODES)
    shutdown_nodes(NODES)