import zmq
from displayarray import display
from tensorcom.tenbin import decode_buffer

ctx = zmq.Context()
s = ctx.socket(zmq.SUB)
s.setsockopt(zmq.SUBSCRIBE, b"topic")
s.connect("tcp://127.0.0.1:7880")

d = display()
while True:
    r = s.recv_multipart()
    # r[0]=="topic"
    arr = decode_buffer(r[1])
    d.update(arr[0], '0')
