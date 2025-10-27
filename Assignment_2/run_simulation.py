# run_simulation.py
import multiprocessing
import subprocess
import logging
import time
import sys

# Logging configruation
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(message)s",
    datefmt= "%d/%m/%Y %H:%M:%S",
    # Added handlers list to include both the file and console stream
    handlers=[
        logging.FileHandler("console.log"),
        # Writing output to terminal
        logging.StreamHandler(sys.stdout)
    ]
)

def launch_node(name, port, is_byzantine=False):
    logging.info(f"Launching {name} on port {port}")
    args = ["python3", "node.py", name, str(port)]
    if is_byzantine:
        args.append("byzantine")
    subprocess.run(args) 

def launch_commander(count, order):
    time.sleep(2)
    logging.info("Launching Commander")
    subprocess.run(["python3", "commander.py", str(count), order])

if __name__ == "__main__":
    print("\n" + "="*60)
    print("    Byzantine Agreement Protocol using RPC")
    print("    WORKS ON LINUX AND MAC TERMINALS ONLY")
    print("="*60)
    print("\nWhat this script does:")
    print("1. Get User input for number of lieutenants, Byzantine nodes, and commander's order")
    print("2. Launches all lieutenants and commander processes")
    print("3. Each lieutenant participates in a single round of the Byzantine Agreement Protocol")
    print("4. Lieutenants communicate via RPC to reach consensus")
    print("5. Logs all messages and decisions in console.log")
    print("6. Commander waits for all lieutenants to finish")
    print("7. Script completes after all processes finish")
    print("="*60 + "\n")
    try:
        count = int(input("Enter number of lieutenants: "))
    except ValueError:
        print("Invalid input. Please enter an integer.")
        sys.exit(1)
        
    # Get Byzantine nodes from user
    byzantine_indices = []
    if count > 0:
        print(f"\nWhich lieutenants should be Byzantine? (1-{count})")
        print("Enter lieutenant numbers separated by commas, or press Enter for none:")
        byzantine_input = input().strip()
        if byzantine_input:
            try:
                byzantine_indices = [int(x.strip()) - 1 for x in byzantine_input.split(',') if x.strip()]
                # Filter valid indices
                byzantine_indices = [i for i in byzantine_indices if 0 <= i < count]
                if byzantine_indices:
                    byzantine_names = [f"Lieutenant-{i+1}" for i in byzantine_indices]
                    print(f"Byzantine nodes: {', '.join(byzantine_names)}")
            except ValueError:
                print("Invalid input for Byzantine nodes. Using no Byzantine nodes.")
                byzantine_indices = []

    # Get commander order from user
    while True:
        order = input("\nEnter the commander's order (ATTACK or RETREAT): ").strip().upper()
        if order in ["ATTACK", "RETREAT"]:
            break
        print("Invalid order. Please enter either 'ATTACK' or 'RETREAT'.") 

    processes = []
    for i in range(count):
        name = f"Lieutenant-{i+1}"
        port = 8001 + i
        is_byzantine = i in byzantine_indices
        p = multiprocessing.Process(target=launch_node, args=(name, port, is_byzantine), name=name)
        processes.append(p)
        p.start()

    commander_process = multiprocessing.Process(target=launch_commander, args=(count, order), name="Commander")
    commander_process.start()

    for p in processes:
        p.join()
    commander_process.join()

    logging.info("Simulation complete.")
    # Keep final print statements for clear completion message on terminal
    print("\n ==== Simulation complete. All processes finished. ====")
    print(" ==== Check 'console.log' for full output. ====")
    sys.exit(0)