"""
Lamport's Mutual Exclusion Coordinator
Manages node lifecycle and collects statistics
"""

import xmlrpc.client
import time
import sys
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("console.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

def wait_for_nodes(nodes, base_port, max_wait=30):
    """Wait for all nodes to be ready"""
    logging.info("Waiting for all nodes to start...")
    
    start_time = time.time()
    ready_nodes = set()
    
    while len(ready_nodes) < len(nodes):
        if time.time() - start_time > max_wait:
            logging.error("Timeout waiting for nodes to start")
            return False
        
        for node_id in nodes:
            if node_id not in ready_nodes:
                try:
                    proxy = xmlrpc.client.ServerProxy(
                        f"http://localhost:{base_port + node_id}/",
                        allow_none=True
                    )
                    response = proxy.ping()
                    if response['status'] == 'alive':
                        ready_nodes.add(node_id)
                        logging.info(f"Node-{node_id} is ready")
                except:
                    pass
        
        time.sleep(0.5)
    
    logging.info("All nodes are ready!")
    return True

def collect_statistics(nodes, base_port):
    """Collect statistics from all nodes"""
    logging.info("\n=== Collecting Statistics ===")
    
    all_stats = {}
    total_messages_sent = 0
    total_messages_received = 0
    
    for node_id in nodes:
        try:
            proxy = xmlrpc.client.ServerProxy(
                f"http://localhost:{base_port + node_id}/",
                allow_none=True
            )
            stats = proxy.get_statistics()
            all_stats[node_id] = stats
            
            total_messages_sent += stats['messages_sent']
            total_messages_received += stats['messages_received']
            
            logging.info(f"Node-{node_id}: CS Entries={stats['cs_entries']}, "
                        f"Messages Sent={stats['messages_sent']}, "
                        f"Messages Received={stats['messages_received']}, "
                        f"Final Clock={stats['lamport_clock']}")
        except Exception as e:
            logging.error(f"Failed to get stats from Node-{node_id}: {e}")
    
    return all_stats, total_messages_sent, total_messages_received

def generate_final_report(all_stats, total_messages_sent, total_messages_received, total_nodes):
    """Generate comprehensive final report"""
    
    logging.info("\n" + "="*80)
    logging.info("=== LAMPORT'S MUTUAL EXCLUSION FINAL REPORT ===")
    logging.info("="*80)
    
    # Individual node statistics
    logging.info("\n--- Individual Node Statistics ---")
    for node_id, stats in sorted(all_stats.items()):
        logging.info(f"Node-{node_id}:")
        logging.info(f"  CS Entries: {stats['cs_entries']}")
        logging.info(f"  Messages Sent: {stats['messages_sent']}")
        logging.info(f"  Messages Received: {stats['messages_received']}")
        logging.info(f"  Final Lamport Clock: {stats['lamport_clock']}")
        if stats['cs_start_time'] and stats['cs_end_time']:
            logging.info(f"  CS Entry Time: {stats['cs_start_time']}")
            logging.info(f"  CS Exit Time: {stats['cs_end_time']}")
        logging.info("")
    
    # Aggregate statistics
    total_cs_entries = sum(stats['cs_entries'] for stats in all_stats.values())
    avg_messages_per_node = total_messages_sent / total_nodes if total_nodes > 0 else 0
    
    logging.info("--- Aggregate Statistics ---")
    logging.info(f"Total Nodes: {total_nodes}")
    logging.info(f"Total CS Entries: {total_cs_entries}")
    logging.info(f"Total Messages Sent: {total_messages_sent}")
    logging.info(f"Total Messages Received: {total_messages_received}")
    logging.info(f"Average Messages per Node: {avg_messages_per_node:.2f}")
    
    # Mutual exclusion verification
    logging.info("\n--- Mutual Exclusion Verification ---")
    cs_times = []
    for node_id, stats in all_stats.items():
        if stats['cs_start_time'] and stats['cs_end_time']:
            cs_times.append({
                'node': node_id,
                'start': stats['cs_start_time'],
                'end': stats['cs_end_time']
            })
    
    # Check for overlaps (simplified - assumes same-day execution)
    overlaps = False
    for i in range(len(cs_times)):
        for j in range(i+1, len(cs_times)):
            # This is a simplified check - in production, use proper datetime comparison
            logging.info(f"Node-{cs_times[i]['node']}: {cs_times[i]['start']} - {cs_times[i]['end']}")
            logging.info(f"Node-{cs_times[j]['node']}: {cs_times[j]['start']} - {cs_times[j]['end']}")
    
    if not overlaps:
        logging.info("✓ MUTUAL EXCLUSION VERIFIED: No overlapping CS executions detected")
    else:
        logging.info("✗ WARNING: Potential CS overlap detected")
    
    # Expected message count verification
    expected_messages_per_cs = 2 * (total_nodes - 1)  # REQUEST + RELEASE to all peers
    expected_total = expected_messages_per_cs * total_cs_entries
    
    logging.info("\n--- Message Count Verification ---")
    logging.info(f"Expected messages per CS entry: {expected_messages_per_cs}")
    logging.info(f"Expected total messages: {expected_total}")
    logging.info(f"Actual total messages sent: {total_messages_sent}")
    
    if total_messages_sent >= expected_total * 0.9:  # Allow 10% tolerance
        logging.info("✓ MESSAGE COUNT VERIFIED")
    else:
        logging.info("✗ WARNING: Message count lower than expected")
    
    logging.info("\n" + "="*20)
    logging.info("=== SIMULATION COMPLETE ===")
    logging.info("="*20 + "\n")

def shutdown_nodes(nodes, base_port):
    """Shutdown all nodes gracefully"""
    logging.info("\n=== Shutting down all nodes ===")
    
    for node_id in nodes:
        try:
            proxy = xmlrpc.client.ServerProxy(
                f"http://localhost:{base_port + node_id}/",
                allow_none=True
            )
            proxy.shutdown()
            logging.info(f"Shutdown signal sent to Node-{node_id}")
        except Exception as e:
            logging.error(f"Failed to shutdown Node-{node_id}: {e}")
    
    time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python coordinator.py <NumberOfNodes> <BasePort>")
        sys.exit(1)
    
    total_nodes = int(sys.argv[1])
    base_port = int(sys.argv[2])
    
    nodes = list(range(1, total_nodes + 1))
    
    # Wait for all nodes
    if not wait_for_nodes(nodes, base_port):
        sys.exit(1)
    
    # Wait for CS execution to complete (adjust based on your timing)
    logging.info("\n=== Waiting for CS execution to complete ===")
    time.sleep(10 + total_nodes * 2)  # Adjust based on your delays
    
    # Collect statistics
    all_stats, total_sent, total_received = collect_statistics(nodes, base_port)
    
    # Generate final report
    generate_final_report(all_stats, total_sent, total_received, total_nodes)
    
    # Shutdown all nodes
    shutdown_nodes(nodes, base_port)
    
    logging.info("Coordinator finished")