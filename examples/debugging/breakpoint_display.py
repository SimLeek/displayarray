from displayarray import breakpoint_display
import numpy as np

center = (75, 450)
zoom = .5
zoom_out = 1.0 / zoom

arr = np.random.uniform(0, 1, (300, 600, 3))
breakpoint_display(arr)

y = np.arange(arr.shape[0])
x = np.arange(arr.shape[1])
y_ = (y - center[0]) * zoom_out / arr.shape[0]
x_ = (x - center[1]) * zoom_out / arr.shape[1]
p = np.array(np.meshgrid(x_, y_))
breakpoint_display(p[0] + .5)
breakpoint_display(p[1] + .5)

barrel_power = 1.5

theta = np.arctan2(p[1], p[0])
breakpoint_display((theta + (np.pi / 2.0)) / (np.pi / 2.0))

radius = np.linalg.norm(p, axis=0)
print(radius.shape)
breakpoint_display(radius)

radius = pow(radius, barrel_power)
breakpoint_display(radius)

print(len(x))
x_new = 0.5 * (radius * np.cos(theta) + 1)
breakpoint_display(x_new)
x_new = np.clip(x_new * len(x), 0, len(x) - 1)
breakpoint_display(x_new / float(len(x)))

y_new = 0.5 * (radius * np.sin(theta) + 1)
breakpoint_display(y_new)
y_new = np.clip(y_new * len(y), 0, len(y) - 1)

p = np.array(np.meshgrid(y, x)).astype(np.uint32)

p_new = np.array((y_new, x_new)).astype(np.uint32)

brr = arr.copy()
brr[p[0], p[1], :] = np.swapaxes(arr[p_new[0], p_new[1], :], 0, 1)
breakpoint_display(brr)

crr = np.zeros_like(arr)
crr[p_new[0], p_new[1], :] = np.swapaxes(arr[p[0], p[1], :], 0, 1)
breakpoint_display(crr)
