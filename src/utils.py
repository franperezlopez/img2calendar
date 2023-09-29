from functools import wraps
import hashlib
from pathlib import Path
import duckdb
import json
import inspect
from typing import Dict, Optional

DEFAULT_CACHE = Path(Path(__file__).absolute().parent.parent / "data" / "cache.ndjson")

def get_key_from_function(func_name, func, args, kwargs):
    # Generate the cache key from the function's arguments.
    # func_name = key_func_name or func.__name__
    # TODO: nicer way to get the arguments
    arguments = list(kwargs.values())
    if len(arguments) == 0:
        arguments = list(map(str, args if not "self" in inspect.signature(func).parameters.keys() else args[1:]))
    key_parts = [func_name] + arguments # list(kwargs.values()) # list(map(str, args if not "self" in inspect.signature(func).parameters.keys() else args[1:]))´
    arguments = '-'.join(key_parts)
    return arguments

def retrieve_by_key(key: str, cache_file: Path = DEFAULT_CACHE):
    conn = duckdb.connect()
    select_script = """SELECT value
    FROM read_ndjson_auto('{cache_file}')
    WHERE key = '{key}'
    """

    if cache_file.exists() and cache_file.stat().st_size > 0:
        result = conn.execute(select_script.format(cache_file=cache_file, key=key)).fetchall()
        if len(result) == 0:
            return None
        return result[0][0]
    else:
        return None

def save(key: str, arguments: str, value: any, cache_file: Path = DEFAULT_CACHE):
    with open(cache_file, "a")  as file:
        file.write(json.dumps({"key": key, "arguments": arguments, "value": value})+"\n")

def cached(cache_file: Path = DEFAULT_CACHE, key_func_name: str = None):
    """
    Decorator that caches the results of the function call.
    """
    if not cache_file.exists():
        cache_file.touch()

    def decorator_cached(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate the cache key from the function's arguments.
            arguments = get_key_from_function(key_func_name or func.__name__, func, args, kwargs)
            key = hashlib.sha1(arguments.encode()).hexdigest()
            result = retrieve_by_key(key, cache_file)

            if result is None:
                # Run the function and cache the result for next time.
                result = func(*args, **kwargs)
                save(key, arguments, result, cache_file)
            else:
                # Skip the function entirely and use the cached value instead.
                print ("Using cached value for key: {}".format(arguments))

            return result
        return wrapper
    return decorator_cached


def try_loads(text: str, fallback_to_text: bool = False) -> Optional[Dict]:
    try:
        if isinstance(text, str):
            return json.loads(text)
    except json.JSONDecodeError:
        pass
    return None if not fallback_to_text else text
