import os
import sys
import json

# Add backend to path to import tools
sys.path.append(os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv(".env", override=True)

from tools.graph_tools import get_tg_connection, get_transaction, get_card_history, get_device_neighbors, detect_card_testing

def test_connection():
    print("Testing TigerGraph connection...")
    conn = get_tg_connection()
    if not conn:
        print("RESULT: FAILED")
        return
        
    print("RESULT: CONNECTED")
    
    # HHG-005 variables
    txn_id = "T_11223344"
    card_id = "C11993-K1"
    customer_id = "C0_999888"
    
    print("\n--- get_transaction(T_11223344) ---")
    res1 = get_transaction(conn, txn_id)
    print(json.dumps(res1, indent=2))
    
    print("\n--- get_card_history(C11993-K1) ---")
    res2 = get_card_history(conn, card_id)
    print(json.dumps(res2, indent=2))
    
    print("\n--- get_device_neighbors(C0_999888) ---")
    res3 = get_device_neighbors(conn, customer_id)
    print(json.dumps(res3, indent=2))

if __name__ == "__main__":
    test_connection()
