"""
Lamport's Distributed Mutual Exclusion Node Server using XML-RPC.
Implements distributed mutual exclusion with logical clocks.
"""

from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import sys
import threading
import time
import heapq
import logging
import os
from datetime import datetime

# Logging configuration - UNIFIED OUTPUT
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
    handlers=[
        logging.FileHandler("console.log", mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Shutdown flag for graceful termination
shutdown_flag = threading.Event()

# Global lock for atomic CS logging
cs_log_lock = threading.Lock()

# ============================================================================
# THREADED XML-RPC SERVER
# ============================================================================

class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    """Multi-threaded XML-RPC server"""
    daemon_threads = True
    allow_reuse_address = True

# ============================================================================
# LAMPORT NODE IMPLEMENTATION
# ============================================================================

class LamportNode:
    """
    Implementation of a node in Lamport's Distributed Mutual Exclusion Algorithm
    """
    
    def __init__(self, node_id, total_nodes, base_port):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.base_port = base_port
        
        # Lamport logical clock
        self.lamport_clock = 0
        self.clock_lock = threading.Lock()
        
        # Request queue (priority queue based on (timestamp, node_id))
        self.request_queue = []
        self.queue_lock = threading.Lock()
        
        # Reply tracking
        self.replies_received = set()
        self.reply_lock = threading.Lock()
        
        # State
        self.requesting_cs = False
        self.in_cs = False
        self.my_request_timestamp = None
        
        # CS execution tracking
        self.cs_entry_count = 0
        self.cs_start_time = None
        self.cs_end_time = None
        
        # Message statistics
        self.messages_sent = 0
        self.messages_received = 0
        
        # Clean up any existing evidence file
        evidence_filename = f"cs_evidence_node_{self.node_id}.txt"
        if os.path.exists(evidence_filename):
            os.remove(evidence_filename)
        
        logging.info(f"[Node-{self.node_id}] Initialized")
        
    def increment_clock(self):
        """Increment Lamport clock"""
        with self.clock_lock:
            self.lamport_clock += 1
            return self.lamport_clock
    
    def update_clock(self, received_timestamp):
        """Update clock based on received timestamp"""
        with self.clock_lock:
            self.lamport_clock = max(self.lamport_clock, received_timestamp) + 1
            return self.lamport_clock
    
    # ==================== RPC Methods (Called by other nodes) ====================
    
    def request_critical_section(self, requesting_node_id, request_timestamp):
        """
        Handle REQUEST message from another node.
        Add to queue and send REPLY back to the requester
        """
        self.messages_received += 1
        current_ts = self.update_clock(request_timestamp)
        
        logging.info(f"[Node-{self.node_id}] Received REQUEST from Node-{requesting_node_id} with TS:{request_timestamp}")
        
        # Add request to queue
        with self.queue_lock:
            heapq.heappush(self.request_queue, (request_timestamp, requesting_node_id))
        
        # Send REPLY back
        reply_ts = self.increment_clock()
        logging.info(f"[Node-{self.node_id}] Sending REPLY to Node-{requesting_node_id} with TS:{reply_ts}")
        
        # Send reply in separate thread with new proxy
        threading.Thread(
            target=self._send_reply_to_node_with_new_proxy,
            args=(requesting_node_id, reply_ts),
            daemon=True
        ).start()
        
        return {'status': 'OK', 'timestamp': reply_ts}
    
    def _send_reply_to_node_with_new_proxy(self, node_id, reply_ts):
        """Send REPLY message to a node using a NEW proxy instance"""
        try:
            import xmlrpc.client
            peer_url = f"http://localhost:{self.base_port + node_id}"
            temp_proxy = xmlrpc.client.ServerProxy(peer_url, allow_none=True)
            temp_proxy.receive_reply(self.node_id, reply_ts)
            self.messages_sent += 1
        except Exception as e:
            logging.error(f"[Node-{self.node_id}] Error sending REPLY to Node-{node_id}: {e}")
    
    def receive_reply(self, replying_node_id, reply_timestamp):
        """Handle REPLY message from another node"""
        self.messages_received += 1
        current_ts = self.update_clock(reply_timestamp)
        
        logging.info(f"[Node-{self.node_id}] ✓ Received REPLY from Node-{replying_node_id} with TS:{reply_timestamp}")
        
        with self.reply_lock:
            self.replies_received.add(replying_node_id)
            replies_count = len(self.replies_received)
        
        logging.info(f"[Node-{self.node_id}] Total replies: {replies_count}/{self.total_nodes-1}")
        
        return {'status': 'OK', 'timestamp': current_ts}
    
    def release_critical_section(self, releasing_node_id, release_timestamp):
        """Handle RELEASE message from another node"""
        self.messages_received += 1
        current_ts = self.update_clock(release_timestamp)
        
        logging.info(f"[Node-{self.node_id}] Received RELEASE from Node-{releasing_node_id} with TS:{release_timestamp}")
        
        # Remove request from queue
        with self.queue_lock:
            self.request_queue = [(ts, nid) for ts, nid in self.request_queue 
                                 if nid != releasing_node_id]
            heapq.heapify(self.request_queue)
        
        return {'status': 'OK', 'timestamp': current_ts}
    
    def ping(self):
        """Health check"""
        return {'status': 'alive', 'node_id': self.node_id}
    
    def get_statistics(self):
        """Return node statistics"""
        return {
            'node_id': self.node_id,
            'cs_entries': self.cs_entry_count,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'lamport_clock': self.lamport_clock,
            'cs_start_time': self.cs_start_time,
            'cs_end_time': self.cs_end_time
        }
    
    def shutdown(self):
        """Graceful shutdown"""
        logging.info(f"[Node-{self.node_id}] Shutting down...")
        shutdown_flag.set()
        return True
    
    # ==================== Critical Section Logic ====================
    
    def execute_cs_cycle(self):
        """Execute one complete CS cycle: Request -> Enter -> Work -> Exit"""
        logging.info(f"[Node-{self.node_id}] Starting CS cycle")
        
        # Request CS
        self.request_cs()
        
        # Wait and enter
        self.wait_for_cs_entry()
        
        # Work in CS
        self.enter_cs()
        
        # Exit CS
        self.exit_cs()
        
        logging.info(f"[Node-{self.node_id}] CS cycle completed")
    
    def request_cs(self):
        """Request to enter Critical Section"""
        self.requesting_cs = True
        
        with self.reply_lock:
            self.replies_received.clear()
        
        # Generate unique request timestamp
        req_ts = self.increment_clock()
        self.my_request_timestamp = req_ts
        
        # Add own request to queue
        with self.queue_lock:
            self.request_queue = [(ts, nid) for (ts, nid) in self.request_queue 
                                 if nid != self.node_id]
            heapq.heappush(self.request_queue, (self.my_request_timestamp, self.node_id))
            queue_str = ', '.join([f"({ts},{nid})" for ts, nid in sorted(self.request_queue)])
            logging.info(f"[Node-{self.node_id}] Queue: [{queue_str}]")
        
        # Send requests to all peers
        import xmlrpc.client
        for peer_id in range(1, self.total_nodes + 1):
            if peer_id != self.node_id:
                threading.Thread(
                    target=self._send_request_to_peer,
                    args=(peer_id, req_ts),
                    daemon=True
                ).start()
        
        logging.info(f"[Node-{self.node_id}] >>> REQUESTING Critical Section with TS:{self.my_request_timestamp}")
    
    def _send_request_to_peer(self, peer_id, req_ts):
        """Send request to a single peer"""
        try:
            import xmlrpc.client
            peer_url = f"http://localhost:{self.base_port + peer_id}"
            proxy = xmlrpc.client.ServerProxy(peer_url, allow_none=True)
            
            logging.info(f"[Node-{self.node_id}] Sending REQUEST to Node-{peer_id} with TS:{req_ts}")
            response = proxy.request_critical_section(self.node_id, req_ts)
            self.messages_sent += 1
            self.update_clock(response['timestamp'])
        except Exception as e:
            logging.error(f"[Node-{self.node_id}] Error sending REQUEST to Node-{peer_id}: {e}")
    
    def wait_for_cs_entry(self):
        """Wait until conditions are met to enter CS"""
        logging.info(f"[Node-{self.node_id}] Waiting for CS entry conditions...")
        
        check_count = 0
        while True:
            with self.reply_lock:
                all_replies = len(self.replies_received) == (self.total_nodes - 1)
                replies_count = len(self.replies_received)
            
            with self.queue_lock:
                if len(self.request_queue) > 0:
                    head_ts, head_nid = self.request_queue[0]
                    at_head = (head_nid == self.node_id)
                else:
                    at_head = False
                
                sorted_queue = sorted(self.request_queue)
                queue_str = ', '.join([f"({ts},{nid})" for ts, nid in sorted_queue[:3]])
            
            check_count += 1
            if check_count % 10 == 0:
                logging.info(f"[Node-{self.node_id}] Checking: Replies={replies_count}/{self.total_nodes-1}, "
                           f"At_head={at_head}, Queue={queue_str}")
            
            if all_replies and at_head:
                logging.info(f"[Node-{self.node_id}] ✓✓✓ All conditions met! Entering CS...")
                break
            
            time.sleep(0.1)
    
    def enter_cs(self):
        """Enter Critical Section"""
        self.cs_entry_count += 1
        self.cs_start_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        enter_ts = self.increment_clock()
        self.in_cs = True
        
        # Use lock to ensure atomic logging of entire CS block
        with cs_log_lock:
            logging.info(f"")
            logging.info(f"[Node-{self.node_id}] ========== ENTERING CRITICAL SECTION ==========")
            logging.info(f"[Node-{self.node_id}] Entry Time: {self.cs_start_time} | Lamport TS: {enter_ts}")
        
        # Perform work
        self.execute_critical_section()
    
    def execute_critical_section(self):
        """Simulate critical section work"""
        work_start_ts = self.increment_clock()
        
        # Collect all operations first, then log atomically
        operations = []
        result = 0
        
        for i in range(3):
            operation_ts = self.increment_clock()
            value = self.node_id * 100 + i * 10
            result += value
            operations.append({
                'num': i+1,
                'value': value,
                'result': result,
                'ts': operation_ts
            })
            time.sleep(0.3)
        
        work_end_ts = self.increment_clock()
        
        # Log all CS work atomically
        with cs_log_lock:
            logging.info(f"[Node-{self.node_id}] Working in CS - Start TS: {work_start_ts}")
            for op in operations:
                logging.info(f"[Node-{self.node_id}]   Operation {op['num']}: +{op['value']} = {op['result']} [TS:{op['ts']}]")
            logging.info(f"[Node-{self.node_id}] Work Complete - Final Result: {result} [TS:{work_end_ts}]")
        
        # Write evidence
        self.write_cs_evidence(result, [f"Op{op['num']}:{op['value']}" for op in operations])
    
    def write_cs_evidence(self, result, operations):
        """Write evidence of CS execution to a file"""
        filename = f"cs_evidence_node_{self.node_id}.txt"
        with open(filename, 'w') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Node: {self.node_id}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Lamport Clock: {self.lamport_clock}\n")
            f.write(f"Request TS: {self.my_request_timestamp}\n")
            f.write(f"Operations: {', '.join(operations)}\n")
            f.write(f"Final Result: {result}\n")
            f.write(f"{'='*60}\n")
    
    def exit_cs(self):
        """Exit Critical Section and send RELEASE"""
        self.cs_end_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        exit_ts = self.increment_clock()
        
        # Log exit atomically
        with cs_log_lock:
            logging.info(f"[Node-{self.node_id}] Exit Time: {self.cs_end_time} | Lamport TS: {exit_ts}")
            logging.info(f"[Node-{self.node_id}] ========== EXITING CRITICAL SECTION ==========")
            logging.info(f"")
        
        self.in_cs = False
        self.requesting_cs = False
        
        # Remove own request from queue
        with self.queue_lock:
            self.request_queue = [(ts, nid) for ts, nid in self.request_queue 
                                 if nid != self.node_id]
            heapq.heapify(self.request_queue)
        
        # Send RELEASE to all peers
        import xmlrpc.client
        for peer_id in range(1, self.total_nodes + 1):
            if peer_id != self.node_id:
                threading.Thread(
                    target=self._send_release_to_peer,
                    args=(peer_id,),
                    daemon=True
                ).start()
    
    def _send_release_to_peer(self, peer_id):
        """Send release to a single peer"""
        try:
            import xmlrpc.client
            peer_url = f"http://localhost:{self.base_port + peer_id}"
            proxy = xmlrpc.client.ServerProxy(peer_url, allow_none=True)
            
            release_ts = self.increment_clock()
            logging.info(f"[Node-{self.node_id}] Sending RELEASE to Node-{peer_id}")
            
            response = proxy.release_critical_section(self.node_id, release_ts)
            self.messages_sent += 1
            self.update_clock(response['timestamp'])
        except Exception as e:
            logging.error(f"[Node-{self.node_id}] Error sending RELEASE to Node-{peer_id}: {e}")

# ============================================================================
# SERVER RUNNER
# ============================================================================

def run_server(node_id, total_nodes, base_port, request_delay):
    """Run node server"""
    node = LamportNode(node_id, total_nodes, base_port)
    
    # Start XML-RPC server
    server_port = base_port + node_id
    server = ThreadedXMLRPCServer(
        ('localhost', server_port),
        allow_none=True,
        logRequests=False
    )
    
    # Register RPC methods
    server.register_instance(node)
    
    logging.info(f"[Node-{node_id}] Started on port {server_port}")
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Wait for all nodes to start
    time.sleep(2)
    
    # Wait before requesting CS
    time.sleep(request_delay)
    
    # Execute CS cycle
    node.execute_cs_cycle()
    
    # Wait for shutdown signal
    while not shutdown_flag.is_set():
        time.sleep(0.5)
    
    # Cleanup
    server.shutdown()
    logging.info(f"[Node-{node_id}] Server stopped")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python lamport_node.py <NodeID> <TotalNodes> <BasePort> <RequestDelay>")
        sys.exit(1)
    
    node_id = int(sys.argv[1])
    total_nodes = int(sys.argv[2])
    base_port = int(sys.argv[3])
    request_delay = float(sys.argv[4])
    
    run_server(node_id, total_nodes, base_port, request_delay)