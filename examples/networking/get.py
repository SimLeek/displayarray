import zmq
from displayarray import DirectDisplay
from tensorcom.tenbin import decode_buffer

ctx = zmq.Context()
s = ctx.socket(zmq.SUB)
s.setsockopt(zmq.SUBSCRIBE, b"topic")
s.connect("tcp://127.0.0.1:7880")

d = DirectDisplay()
while True:
    r = s.recv_multipart()
    # r[0]=="topic"
    arr = decode_buffer(r[1])
    for i, a in enumerate(arr):
        d.imshow(f'{i}', a)
    d.update()
