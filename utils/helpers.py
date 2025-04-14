import time

def sleep_print(seconds, msg=None):
    if msg:
        print(msg)
    time.sleep(seconds)
