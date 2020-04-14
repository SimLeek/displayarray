from displayarray import read_updates, display
import time
import cProfile
from examples.videos import test_video


def profile_reading(total_seconds=5):
    t_init = t01 = time.time()
    times = []
    started = False
    for up in display(1, size=(1, 1)):
        if up:
            t1 = time.time()
            if started:
                times.append((t1 - t01) * 1000)
            t01 = t1
            started = True
        if started:
            t2 = time.time()
            if t2 - t_init >= total_seconds:
                if times:
                    print(f"Average framerate: {1000 / (sum(times) / len(times))}fps")
                else:
                    print("failure")
                break
        else:
            t_init = time.time()


cProfile.run("profile_reading()")
