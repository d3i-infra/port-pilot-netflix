import hashlib

def str_to_probability(in_str: str) -> float:
    """
    Return a reproducible uniformly random float in the interval [0, 1) for the given string.
    """
    max_hash_plus_one = 2**(hashlib.sha512().digest_size * 8)
    hash_digest = hashlib.sha512(in_str.encode()).digest()
    hash_int = int.from_bytes(hash_digest, 'big')  
    float_from_zero_to_one = hash_int / max_hash_plus_one

    return float_from_zero_to_one 


def assign_experiment_group(in_str) -> str:
    """
    Returns an experimental condition label based on an input string. 
    The same input string will always result in the same label.
    """
    try:
        draw = str_to_probability(in_str)

        if draw < 0.5:
            return "A"
        else:
            return "B"
    except Exception as e:
        pass

    return "A"
