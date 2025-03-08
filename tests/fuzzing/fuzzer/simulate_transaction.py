def simulate_transaction(w3, contract, function_name, inputs=None, value=0):
    try:
        if inputs:
            # Sorting inputs accordingly with function parameters
            sorted_inputs = [inputs[param['name']] for param in contract.functions[function_name].abi['inputs']]
            txn = getattr(contract.functions, function_name)(*sorted_inputs).transact({'value': value})
        else:
            txn = getattr(contract.functions, function_name)().transact({'value': value})
        tx_receipt = w3.eth.wait_for_transaction_receipt(txn)
          # Capture return value if function has output
        return_value = getattr(contract.functions,function_name)().call() if inputs is None else None
               
       # print(f"Transaction '{function_name}' executed successfully: {tx_receipt.transactionHash.hex()}")

        try:
            return_value = getattr(contract.functions,function_name)(*sorted_inputs).call() if inputs else getattr(contract.functions,function_name)().call()
        except Exception:
            return_value = None
        return tx_receipt,return_value
    

    except Exception as e:
        print(f"Error during transaction '{function_name}' execution: {e}")
        return None,None
