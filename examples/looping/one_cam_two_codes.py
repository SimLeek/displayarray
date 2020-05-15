from displayarray import read_updates

with read_updates(0) as a, read_updates(0) as b:
    for i in range(1000):
        a.update()
        b.update()
        try:
            print(a.frames == b.frames)
        except ValueError:
            print(f"frame comparison: {(a.frames['0'][0] == b.frames['0'][0]).all()}")
