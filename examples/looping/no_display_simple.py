from displayarray import read_updates

for f in read_updates(0, size=(1, 1)):
    if f:
        print(f[0].shape)
        break
