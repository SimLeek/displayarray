from displayarray import read_updates
import numpy as np
import zmq
from tensorcom.tenbin import encode_buffer

def black_and_white(arr):
    return (np.sum(arr, axis=-1) / 3).astype(np.uint8)


import time

t0 = t1 = time.time()

ctx = zmq.Context()
s = ctx.socket(zmq.PUB)
s.bind("tcp://127.0.0.1:7880")

for up in read_updates(0, size=(9999,9999)):
    if up:
        t1 = time.time()
        u = next(iter(up.values()))[0]
        s.send_multipart([b'topic', encode_buffer([u])])
        print(1.0 / (t1 - t0))
        t0 = t1


