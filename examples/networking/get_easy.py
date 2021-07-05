from displayarray import display
import time

t0 = time.time()
for up in display("tcp://127.0.0.1:7880#topic"):
    if up:
        t1 = time.time()
        u = next(iter(up.values()))[0]
        print(1.0 / (t1 - t0))
        t0 = t1