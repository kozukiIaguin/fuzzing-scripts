
from utils.random_inputs import *
from fuzzer.simulate_transaction import *
from code_coverage.code_coverage import *
from detector.reentrancy import *
import random

def genetic_fuzzer(w3, abi, contract_instance, sloads, calls,source_map, generations=10, population_size=10):
    
    population = [generate_random_test_case(abi) for _ in range(population_size)]
    random.shuffle(population)#just to do it more random
    coverage_map = {}
    total_pcs = len(source_map.instr_positions)#all contract pcs
    stored_values ={} #dict to store return values from functions without inputs
 
    for generation in range(generations):
        print(f"\nGeneration {generation}...")
        fitness_scores = []
        for test_case in population:
           
            func_name = test_case['name']
            func_inputs = test_case['inputs'] if len(test_case['inputs']) > 0 else None # Always empty for EtherStore!
            func_state = test_case['stateMutability']
            value = 0
                
            if func_state == 'payable':
                value = random.randint(1, 10**18)  # Deposit between 1 wei and 1 ether
                print(f"Transaction `{func_name}` received random input value: {value}")
            tx_receipt,return_value = simulate_transaction(w3, contract_instance, func_name, func_inputs, value)
            
            # Check instructions
            result = w3.manager.request_blocking('debug_traceTransaction', [f"{tx_receipt.transactionHash.hex()}"])
            logs = result["structLogs"] if "structLogs" in result else []
            new_coverage = code_coverage(logs)
            update_coverage(coverage_map, new_coverage)
            

            #Stores return values of functions without inputs
            if return_value is not None and func_inputs is None:
                stored_values[func_name] = return_value
            
            fitness = len(new_coverage - set(coverage_map.keys())) #more new paths for higher fitness
            fitness_scores.append((test_case,fitness))

            #select the top 50% best test cases by
            fitness_scores.sort(key=lambda x: x[1],reverse=True)
            selected_population = [x[0] for x in fitness_scores[:population_size // 2]]


            #Crossover section

            new_population = []
            while len(new_population) < population_size:
                parent1,parent2 = random.sample(selected_population,2)

                #if one of the parents has inputs, mix the sorted value
                
                if parent1["name"] in stored_values and parent2["inputs"]:
                    param_to_replace = random.choice(list(parent2["inputs"].keys()))
                    parent2["inputs"][param_to_replace] = stored_values[parent1["name"]]
                
                child = crossover(parent1,parent2)
                new_population.append(child)
                population = new_population
                calculate_coverage(coverage_map,total_pcs)












            if not result.failed:
                for i, instruction in enumerate(result.structLogs):
                    pc = detect_reentrancy(sloads, calls, instruction)
        
        calculate_coverage(coverage_map, total_pcs)
