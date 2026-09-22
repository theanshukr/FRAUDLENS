import json
import os

cases = ["cases/HHG-001.json", "cases/HHG-002.json", "cases/HHG-004.json", "cases/HHG-005.json", "cases/HHG-017.json"]

for case_file in cases:
    if not os.path.exists(case_file):
        continue
    
    with open(case_file, "r") as f:
        data = json.load(f)
    
    c_id = data.get("case_id")
    card = data.get("card_id")
    
    if c_id == "HHG-001":
        # Simple transaction relationship graph
        txn = "T_9988776655"
        cust = "C_88776655"
        data["txn_id"] = txn
        data["customer_id"] = cust
        
        for ev in data.get("evidence", []):
            ref = ev.get("ref", "")
            if ref == "get_transaction":
                ev["entity_ids"] = [txn]
            elif ref == "get_card_history":
                ev["entity_ids"] = [card, cust] # CARD -> CUSTOMER
            elif ref == "get_device_neighbors":
                ev["entity_ids"] = [txn, "D_55443322"] # TXN -> DEVICE
                
    elif c_id == "HHG-002":
        # customer/account/card/device graph
        txn = "T_2233445566"
        cust = "C0_334455"
        dev1 = "D_111222"
        dev2 = "D_333444"
        data["txn_id"] = txn
        data["customer_id"] = cust
        
        for ev in data.get("evidence", []):
            ref = ev.get("ref", "")
            if ref == "get_transaction":
                ev["entity_ids"] = [txn]
            elif ref == "get_card_history":
                ev["entity_ids"] = [card, cust]
            elif ref == "get_device_neighbors":
                ev["entity_ids"] = [card, dev1, dev2] # CARD -> DEV1 -> DEV2
            elif ref == "find_connected_cards":
                ev["entity_ids"] = [dev2, "CARD_XYZ"]
                
    elif c_id == "HHG-004":
        # transaction/device/merchant graph (using IP for merchant logic/location)
        txn = "T_5566778899"
        dev = "D_998877"
        merch = "M_12345" # Unmapped, will default to "Entity"
        data["txn_id"] = txn
        
        for ev in data.get("evidence", []):
            ref = ev.get("ref", "")
            if ref == "get_transaction":
                ev["entity_ids"] = [txn]
            elif ref == "get_card_history":
                ev["entity_ids"] = [card, merch]
            elif ref == "get_device_neighbors":
                ev["entity_ids"] = [txn, dev]
            elif ref == "find_connected_cards":
                ev["entity_ids"] = [dev, card]
                
    elif c_id == "HHG-005":
        # multi-entity investigation
        txn = "T_11223344"
        cust = "C0_999888"
        dev = "DEVICE_A1B2"
        data["txn_id"] = txn
        data["customer_id"] = cust
        
        for ev in data.get("evidence", []):
            ref = ev.get("ref", "")
            if ref == "get_transaction":
                ev["entity_ids"] = [txn]
            elif ref == "get_card_history":
                ev["entity_ids"] = [card, cust]
            elif ref == "get_device_neighbors":
                ev["entity_ids"] = [cust, dev]
            elif ref == "detect_card_testing":
                ev["entity_ids"] = [card, txn, dev]
                
    elif c_id == "HHG-017":
        # more complex suspicious relationship graph
        txn = "T_99990000"
        cust = "C_112233"
        dev1 = "D_AAABBB"
        dev2 = "D_CCCDDD"
        card2 = "CARD_X9Y8"
        data["txn_id"] = txn
        data["customer_id"] = cust
        
        for ev in data.get("evidence", []):
            ref = ev.get("ref", "")
            if ref == "get_transaction":
                ev["entity_ids"] = [txn]
            elif ref == "get_card_history":
                ev["entity_ids"] = [card, cust]
            elif ref == "get_device_neighbors":
                ev["entity_ids"] = [txn, dev1, dev2]
            elif ref == "find_connected_cards":
                ev["entity_ids"] = [dev2, card2]
            elif ref == "detect_velocity_anomaly":
                ev["entity_ids"] = [cust, dev1]
            elif ref == "search_similar_cases":
                ev["entity_ids"] = [card, "CC-0099"]
                
    # Also update the case.evidence mirror if it exists
    if "case" in data and "evidence" in data["case"]:
        data["case"]["evidence"] = data["evidence"]
        
    with open(case_file, "w") as f:
        json.dump(data, f, indent=2)

print("Enrichment complete.")
