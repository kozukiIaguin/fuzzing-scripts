import random
import struct
import json
from z3 import *

#Section for genetic alg.

class Chromossome:
    def __init__(self,function_name,parameters):
        
        """
        This class initializes a chromossome with a function name and input parameters
        
        The param 'parameters' is a dictionary containing the parameters names, raw data and values

        Example: function_name = "transfer"
                 parameters = {"to": "address", "amount":100} 
        """
        self.function_name = function_name
        self.parameters = parameters
        
    def to_bytes(self):
        #Converts the chromosomes parameters into a byte array

        byte_representation = bytearray()

        for key,value in self.parameters.items():
            if isinstance(value,int):
                byte_representation.extend(struct.pack(">Q",value)) # (>Q is the big endian(>) and the unsigned 8-byte int)
            elif isinstance(value,str):
                byte_representation.extend(value.encode("utf-8")) #extend method appends a sequence of bytes
            elif isinstance(value,bool):
                byte_representation.append(1 if value else 0)
            elif isinstance(value,bytes):
                byte_representation.extend(value)
            else:
                raise ValueError(f"Unsupported data tyoe for parameter {key}")
        return byte_representation

    def from_bytes(function_name,byte_data,param_types):

        """
        This function converts a byte array back into the structured parameters

        byte_data = byte array represantig the parameters
        param_type: its a list o tuples (param_name, param_type)

        this func returns a a chromossome instance
        """        
        
        parameters = {}
        offset = 0
         # offset is the track for the byte array, to track out position on it

        for param_name, param_type in param_types:
            if param_type == "uint256":
                parameters[param_name] = struct.unpack(">Q",byte_data[offset:offset+8])[0]
                offset+=8
            elif param_type == "address":
                parameters[param_name] = "0x" + byte_data[offset:offset+20].hex()
                offset+=20
            elif param_type == "bool":
                parameters[param_name] = bool(byte_data[offset])
                offset +=1
            elif param_type =="string":
                str_end = byte_data.find(b'\x00', offset) #finds the null terminator for the string
                parameters[param_type] = byte_data[offset:str_end].decode("utf-8")
                offset = str_end + 1
            elif param_type.startswith("bytes"):
                size = int(param_type.replace("bytes","")) if len(param_type) > 5 else 32
                parameters[param_name] = byte_data[offset:offset+size]
            else:
                raise ValueError(f"Unsupported type: {param_type}")

        return Chromossome(function_name,parameters)        

    def __repr__(self):
        return f"Chromossome(Function: {self.function_name}, Parameters: {self.parameters})"




def random_value(param_type):
  
    if param_type == "uint256":
        return random.randint(0, 2**256 - 1)  

    elif param_type == "address":
        return "0x" + "".join(random.choices("0123456789abcdef", k=40))  

    elif param_type == "bool":
        return random.choice([True, False]) 

    elif param_type == "string":
        length = random.randint(5, 20)  
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", k=length))

    elif param_type.startswith("bytes"):
        size = int(param_type.replace("bytes", "")) if len(param_type) > 5 else random.randint(1, 32)
        return bytes(random.getrandbits(8) for _ in range(size))

    else:
        return None  

def generate_random_test_case(abi):
    """
    Generates a test case with random inputs. If the function has no inputs, it returns None.
    """
    function = random.choice(abi)
    function_name = function["name"]
    parameters = {}

    if "inputs" in function and function["inputs"]:  # Function inputs
        for param in function["inputs"]:
            parameters[param["name"]] = random_value(param["type"])  
    else:
        parameters = None  # No inputs

    return {"name": function_name, "inputs": parameters}

def crossover(test_case1,test_case2,stored_values):
    #This func mixes 2 test cases by combining their inputs

    if test_case1["inputs"] is None or test_case2["inputs"] is None:
        return test_case1 #if one of the functions have no inputs, return it unchanged
    
    child = test_case1.copy()
    for key in test_case2["inputs"]:
        if key in child["inputs"] and random.random() < 0.5:
            if test_case1["name"] in stored_values: #if avaliable, use stored values
                child["inputs"][key] = stored_values[test_case1["name"]]
                
                expected_type = next((param["type"] for func in abi if func["name"]))
            # else:
            #     child["inputs"][key] = test_case2["inputs"][key]#otherwise use the crossover
    return child



























#All the mutation methods from afl work with bytearray input
def flip_bits(buffer:bytearray):
    if not buffer:
        return
    num_bits = random.randint(0,len(buffer)* 8)
    for _ in range(num_bits):
        bit_pos = random.randint(0,len(buffer)* 8-1)
        buffer[bit_pos // 8] ^=(1<< (bit_pos & 8))


def set_interesting_values(buffer:bytearray):
    if not buffer:
        return
    interesting_8 = random.randint(0,len(buffer)-1)
    interesting_16 = [0x0000,0xFFFF, 0x7FFF]
    interesting_32 = [0x00000000, 0xFFFFFFFF, 0x7FFFFFFF]
    
    pos = random.randint(0,len(buffer)-1)
    choice = random.randint(0,2)

    if choice == 0:
        buffer[pos] = random.choice(interesting_8);

    elif choice == 1 and pos + 1 < len(buffer):
        buffer[pos:pos+2] = struct.pack('<H', random.choice(interesting_16))
    
    elif choice == 2 and pos + 3 < len(buffer):
        buffer[pos:pos+4] = struct.pack('I',random.choice(interesting_32))

def delete_bytes(buffer:bytearray):
    if len(buffer) <= 1:
        return
    del_len = random.randint(1,len(buffer) // 2)
    del_pos = random.randint(0,len(buffer) - del_len)
    del buffer[del_pos:del_pos + del_len]


def duplicate_bytes(buffer:bytearray):
    max_size = 1024
    if(len(buffer) >= max_size or len(buffer) <=1):
        return
    dup_len = random.randint(1, len(buffer) //2)
    dup_pos = random.randint(0, len(buffer) - dup_len)
    if len(buffer) + dup_len > max_size:
        dup_len = max_size - len(buffer)
    buffer.extend(buffer[dup_pos:dup_pos + dup_len])

def insert_random_bytes(buffer:bytearray):
    max_size = 1024
    if len(buffer) >= max_size:
        return
    insert_len = random.randint(0, max_size - len(buffer))
    insert_pos = random.randint(0,len(buffer))
    random_bytes = bytearray(random.randint(0,255) for _ in range(insert_len))

def add_subtract_random(buffer:bytearray):
    if not buffer:
        return
    pos = random.randint(0,len(buffer) -1)
    change = random.randint(-10,10)
    buffer[pos] = (buffer[pos] + change) % 256

#Function to select witch mutation will be used
def mutate_inputs(buffer: bytearray):
    if not buffer:
        return
    mutation = random.randint(1, 6)  

    if mutation == 1:
        return flip_bits(buffer)
    elif mutation == 2:
        return add_subtract_random(buffer)
    elif mutation == 3:
        return set_interesting_values(buffer)
    elif mutation == 4:
        return duplicate_bytes(buffer)
    elif mutation == 5:
        return insert_random_bytes(buffer)
    elif mutation == 6:
        return delete_bytes(buffer)
