LOG_RATE_LIMIT_CALLS = False
RATE_LIMIT_CALLS = 0


def enable_rate_limit_logging():
    global LOG_RATE_LIMIT_CALLS
    LOG_RATE_LIMIT_CALLS = True


def log_rate_limited_call(name):
    global LOG_RATE_LIMIT_CALLS
    global RATE_LIMIT_CALLS

    if LOG_RATE_LIMIT_CALLS:
        RATE_LIMIT_CALLS += 1
        print(f"{RATE_LIMIT_CALLS}. Rate limited call: {name}")
