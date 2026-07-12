import numpy as np
import cv2
import struct
import os
import rectpack
from displayarray.font.get_texture_atlas import get_or_create_font_npz
import glfw
import moderngl
import time
from typing import Union

SparseType = None
try:
    import torch
    pytorch_available = True
    SparseType = Union[SparseType, torch.Tensor]
except ImportError:
    pytorch_available = False

try:
    import scipy
    scipy_available = True
    SparseType = Union[SparseType, scipy.sparse.csr_matrix]
except ImportError:
    scipy_available = False

dir_path = os.path.dirname(os.path.realpath(__file__))

def pad_8_to_32(arr):
    pad_len = -arr.size * np.dtype(arr.dtype).itemsize % np.dtype(np.float32).itemsize
    if pad_len != 0:
        arr = np.pad(arr.flatten(), (0, pad_len))
    return arr.flatten().view(np.float32)

class InputTextureInfosUBO(object):
    def __init__(self, start_textures=[]):
        self.channels = 3  # Assuming RGB format
        self.tex_levels = []
        self.csr_levels = []  # include start pointers and interleaved or not indices
        self.input_image = []
        self.input_csr_value_indices = []
        self.input_csr_index_pointers = []
        self.names = []
        self.no_input = not bool(start_textures)

    def append_input_stream(self, img:np.ndarray, name="Unnamed", flags:int=0):
        i = len(self.tex_levels)
        if i==0:
            start_index = 0
        else:
            start_index = self.tex_levels[-1]['startIdx']+\
                          self.tex_levels[-1]['width']*self.tex_levels[-1]['height']*self.tex_levels[-1]['channels']
        width = img.shape[1]
        height = img.shape[0]
        if len(img.shape)==2:
            channels = 1
        else:
            channels = img.shape[2]
        rect = [0,0,width,height]
        self.tex_levels.append({
            'startIdx': start_index,
            'width': width,
            'height': height,
            'flags': flags,
            'channels': channels,
            'rect': rect
        })
        if isinstance(self.input_image, bytes):
            self.input_image = bytearray(self.input_image)
        self.input_image.append((img, start_index))
        self.names.append(name)

        return i

    def set_input_stream(self, i, img:np.ndarray, name = None, flags:int=0):
        # todo: deal with setting index that doesn't exist
        start_index = self.tex_levels[i]['startIdx']
        if len(img.shape)==2:
            channels = 1
        else:
            channels = img.shape[2]
        if i!=len(self.tex_levels) and \
            self.tex_levels[i]['width']*self.tex_levels[i]['height']!=img.shape[0]*img.shape[1]:
            ind = start_index
            for j in range(i, len(self.tex_levels)):
                new_start_index = ind + img.shape[0]*img.shape[1]*channels
                self.tex_levels[j]['startIdx'] = new_start_index
                ind = new_start_index

        self.tex_levels[i]['width'] = img.shape[0]
        self.tex_levels[i]['height'] = img.shape[1]
        self.tex_levels[i]['flags'] = flags
        self.tex_levels[i]['channels'] = channels

        if isinstance(self.input_image, bytearray):
            self.input_image = bytes(self.input_image)
        if name is not None:
            self.names[i] = name
        else:
            self.names[i] = f"Unnamed {i}"

        # It seems to be stuck at 200MBps, and this might be a python problem.
        # zero-copy would definitely speed things up, but I'm not sure it's possible with OpenCV
        # Memcpy should be 10-100 times faster at about 2-20GBps though,
        # so if you can access & set the raw data from c++, then that would speed things up 100x
        #
        # Tried these. Didn't work:
        #     self.input_image[start_index:end_index] = img.flat
        #     memoryview(self.input_image)[start_index*4:end_index*4] = memoryview(img.tobytes())  # inpu_image is a bytearray here
        #     memmove(id(self.input_image)+0x20+start_index*4, id(img.tobytes())+0x20, 4*(end_index-start_index))
        #     Mem.view(self.input_image)[start_index*4:end_index*4] = img.data
        # an alternative would be to store a list of pointers to img.data or tobytes() and their sizes & offsets, then use write with offset for setting the buffer
        #np.copyto(self.input_image[start_index:end_index], img.flat, casting='no')
        #img = pad_8_to_32(img)
        self.input_image[i] = (img, start_index)

    def append_csr_input_stream(self, img:SparseType, name="Unnamed", flags:int=0):
        i = len(self.tex_levels)
        if i==0:
            start_index = 0
        else:
            start_index = self.tex_levels[-1]['startIdx']+\
                          self.tex_levels[-1]['width']*self.tex_levels[-1]['height']*self.tex_levels[-1]['channels']
        width = img.shape[1]
        height = img.shape[0]
        if len(img.shape)==2:
            channels = 1
        else:
            channels = img.shape[2]
        rect = [0,0,width,height]
        self.tex_levels.append({
            'startIdx': start_index,
            'width': width,
            'height': height,
            'flags': flags,
            'channels': channels,
            'rect': rect
        })
        if isinstance(self.input_image, bytes):
            self.input_image = bytearray(self.input_image)
        self.input_image.append((img, start_index))
        self.names.append(name)

        return i

    def set_csr_input_stream(self, i, img:SparseType, name = None, flags:int=0):
        # todo: deal with setting index that doesn't exist
        start_index = self.tex_levels[i]['startIdx']
        if len(img.shape)==2:
            channels = 1
        else:
            channels = img.shape[2]
        if i!=len(self.tex_levels) and \
            self.tex_levels[i]['width']*self.tex_levels[i]['height']!=img.shape[0]*img.shape[1]:
            ind = start_index
            for j in range(i, len(self.tex_levels)):
                new_start_index = ind + img.shape[0]*img.shape[1]*channels
                self.tex_levels[j]['startIdx'] = new_start_index
                ind = new_start_index

        self.tex_levels[i]['width'] = img.shape[0]
        self.tex_levels[i]['height'] = img.shape[1]
        self.tex_levels[i]['flags'] = flags
        self.tex_levels[i]['channels'] = channels

        if isinstance(self.input_image, bytearray):
            self.input_image = bytes(self.input_image)
        if name is not None:
            self.names[i] = name
        else:
            self.names[i] = f"Unnamed {i}"

        # It seems to be stuck at 200MBps, and this might be a python problem.
        # zero-copy would definitely speed things up, but I'm not sure it's possible with OpenCV
        # Memcpy should be 10-100 times faster at about 2-20GBps though,
        # so if you can access & set the raw data from c++, then that would speed things up 100x
        #
        # Tried these. Didn't work:
        #     self.input_image[start_index:end_index] = img.flat
        #     memoryview(self.input_image)[start_index*4:end_index*4] = memoryview(img.tobytes())  # inpu_image is a bytearray here
        #     memmove(id(self.input_image)+0x20+start_index*4, id(img.tobytes())+0x20, 4*(end_index-start_index))
        #     Mem.view(self.input_image)[start_index*4:end_index*4] = img.data
        # an alternative would be to store a list of pointers to img.data or tobytes() and their sizes & offsets, then use write with offset for setting the buffer
        #np.copyto(self.input_image[start_index:end_index], img.flat, casting='no')
        #img = pad_8_to_32(img)
        self.input_image[i] = (img, start_index)

    def get_name_str_buffers(self, start_index=0, num_strings=None):
        # note: start index will tell which section these strings start at, so menu items can use other string sections
        # note2: if num_strings is an int, we'll set the start, otherwise we return part of all sections
        name_bytes = bytearray()
        name_ptr_bytes = bytearray()

        if start_index==0:
            if num_strings is None:
                name_ptr_bytes.extend(struct.pack("<1i", len(self.names)))
                #name_ptr_bytes.extend(struct.pack("<1ixxxxxxxxxxxx", len(self.names)))
            else:
                name_ptr_bytes.extend(struct.pack("<1i", len(self.names)))
                #name_ptr_bytes.extend(struct.pack("<1ixxxxxxxxxxxx", num_strings))
        name_ptrs = [start_index]
        for name in self.names:
            name_ptrs.append(name_ptrs[-1]+len(name))
        if len(name_ptrs)%4!=0:
            name_ptrs.extend([name_ptrs[-1]]*int(-len(name_ptrs)%4))
        name_ptr_bytes.extend(struct.pack(f"<{len(name_ptrs)}i", *name_ptrs))
        for name in self.names:
            name_bytes.extend(struct.pack(f"<{len(name)}i", *[ord(n) for n in name]))
        return name_bytes, name_ptr_bytes


    def get_tex_data_buffer(self):
        tex_data_bytes = bytearray()
        # glsl is alligned to vec4 or 128 bits or 32 bytes (32 xs)
        tex_data_bytes.extend(struct.pack("<1ixxxxxxxxxxxx", len(self.tex_levels)))
        for level in self.tex_levels:
            tex_data_bytes.extend(struct.pack("<5i"+"x"*4*3, level['startIdx'], level['width'], level['height'], level['flags'], level['channels'])) # todo: add 4th int holding flags (rgb order, w/h order)
            tex_data_bytes.extend(struct.pack("<4f", *level['rect']))
        return bytes(tex_data_bytes)

    def set_tex_data_buffer(self, data):  # todo: unusued, remove or update
        if len(data) - 2 % 7 != 0:
            raise ValueError("Input data size does not match buffer format")
        self.channels = data[0]
        num_levels = data[1]
        for i in range(num_levels):
            self.tex_levels[i]['startIdx'] = data[i * 7 + 2]
            self.tex_levels[i]['width'] = data[i * 7 + 3]
            self.tex_levels[i]['height'] = data[i * 7 + 4]
            self.tex_levels[i]['rect'] = data[i * 7 + 5:i * 7 + 9]

    def append_tex_data_buffer(self, data):  # todo: unusued, remove or update
        if len(data) != 7:
            raise ValueError("Input data size does not match buffer format")
        self.tex_levels.append({
            'startIdx': data[0],
            'width': data[0],
            'height': data[0],
            'rect': data[0]
        })

    def get_tex_level_rect(self, level_idx):
        return self.tex_levels[level_idx]['rect']

    def set_tex_level_rect(self, level_idx, rect):
        if len(rect) != 4:
            raise ValueError("Rect must contain 4 values (vec4)")
        self.tex_levels[level_idx]['rect'] = rect

    def get_input_image_buffer(self, writer):
        for t in self.input_image:
            img, start = t
            writer(img.data, offset=start)
        #return bytes(self.input_image)

    def set_input_image_buffer(self, data: np.ndarray):
        if len(data) != len(self.input_image):
            raise ValueError("Input data size does not match buffer size")
        self.no_input = False
        self.input_image = data.flatten()

    def append_input_image_buffer(self, data: np.ndarray):
        if len(data) != len(self.input_image):
            raise ValueError("Input data size does not match buffer size")
        if self.no_input:
            self.input_image = data.flatten()
            self.no_input = False
        else:
            self.input_image = np.concatenate((self.input_image, data.flatten()), axis=0, dtype=self.input_image.dtype)

class UserInputUBO:
    def __init__(self):
        self.sel_lvl = np.zeros((1), np.int32)
        self.iMouse = np.zeros((2,), np.float32)

    def to_bytes(self):
        return struct.pack(f"<ixxxxff", *self.sel_lvl, *self.iMouse)

    @property
    def nbytes(self):
        return len(self.to_bytes())

class UserOutputUBO:
    def __init__(self):
        self.hit_level = -1
        self.hit_pos = (-1.0, -1.0)

    def to_bytes(self):
        return struct.pack(f"<ixxxxff", self.hit_level, *self.hit_pos)

    @property
    def nbytes(self):
        return len(self.to_bytes())

class MglApp:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.user_input_ubo = UserInputUBO()
        self.user_output_ubo = UserOutputUBO()
        self.input_texture_infos_ubo = InputTextureInfosUBO()
        self.buffers = {}
        self.create_shaders()

    def create_shaders(self):
        self.vertex_shader = """
            #version 430
            in vec2 in_position;
            in vec4 in_texcoord_0;
            
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
            }
        """
        with open(os.path.join(dir_path, "pyr_quads.frag")) as f:
            self.fragment_shader = f.read()
        self.shader = self.ctx.program(vertex_shader=self.vertex_shader, fragment_shader=self.fragment_shader)

        buffer_sizes = {
            'input_texture': 4 * 1920 * 1080 * 4 * 3,
            'input_texture_infos': 4 * 30 * 9 * 4 + 4 * 2,
            'user_input': len(UserInputUBO().to_bytes()),
            'user_output': len(UserOutputUBO().to_bytes()),
            'font_image': np.load(get_or_create_font_npz(), allow_pickle=True)['atlas_texture'].size * 2 + 8,
            'glyph_buffer': 33 * len(np.load(get_or_create_font_npz(), allow_pickle=True)['metadata'].item()),
            'input_name': 16384,
            'input_name_ptr': 1024
        }
        for i, (name, size) in enumerate(buffer_sizes.items()):
            buffer = self.ctx.buffer(reserve=size, dynamic=True)
            buffer.bind_to_storage_buffer(i)
            self.buffers[name] = {
                'buffer': buffer,
                'size': size,
            }
        self.update_buffers()

        npz_data = np.load(get_or_create_font_npz(), allow_pickle=True)
        self.buffers['font_image']['buffer'].write(self.load_atlas_image_data(npz_data))
        self.buffers['glyph_buffer']['buffer'].write(self.load_atlas_glyph_data(npz_data))

        self.quad_fs = self.ctx.buffer(np.array([
            -1.0, -1.0,
             1.0, -1.0,
             1.0,  1.0,
            -1.0, -1.0,
             1.0,  1.0,
            -1.0,  1.0
        ], dtype=np.float32))
        self.vao = self.ctx.vertex_array(self.shader, [(self.quad_fs, '2f', 'in_position')])

    def write_buffer(self, data, offset, buffer_name):
        buffer = self.buffers[buffer_name]['buffer']
        data_bytes = data.tobytes() if isinstance(data, np.ndarray) else data
        buffer[offset:offset + len(data_bytes)] = data_bytes
        self.ctx.memory_barrier(barriers=moderngl.SHADER_STORAGE_BARRIER_BIT)

    def load_atlas_glyph_data(self, npz_data):
        atlas_data = npz_data['metadata'].item()
        atlas_data_bytes = bytearray()
        atlas_data_bytes.extend(struct.pack("<1i", len(atlas_data)))
        for c, bbox in atlas_data.items():
            atlas_data_bytes.extend(struct.pack("<5i", ord(c), bbox[1], bbox[0], bbox[3], bbox[2]))
        return bytes(atlas_data_bytes)

    def load_atlas_image_data(self, npz_data):
        atlas_data = npz_data['atlas_texture']
        atlas_data_bytes = bytearray()
        atlas_data_bytes.extend(struct.pack("<2i", *atlas_data.shape))
        atlas_data_bytes.extend(atlas_data.tobytes())
        return bytes(atlas_data_bytes)

    def update_buffers(self):
        self.input_texture_infos_ubo.get_input_image_buffer(
            lambda data, offset: self.buffers['input_texture']['buffer'].write(data, offset=offset)
        )
        self.buffers['input_texture_infos']['buffer'].write(self.input_texture_infos_ubo.get_tex_data_buffer())
        names, name_ptrs = self.input_texture_infos_ubo.get_name_str_buffers()
        self.buffers['input_name']['buffer'].write(names)
        self.buffers['input_name_ptr']['buffer'].write(name_ptrs)
        self.buffers['user_input']['buffer'].write(self.user_input_ubo.to_bytes())

    def update(self, width, height):
        self.ctx.clear(1.0, 1.0, 1.0, 1.0)
        self.ctx.viewport = (0, 0, width, height)
        self.update_buffers()
        self.vao.render()

class GlfwWindow:
    def __init__(self, title="GLFW Window", width=800, height=600, vsync=True):
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
        self.window = glfw.create_window(width, height, title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")
        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context(require=430)
        self.app = MglApp(self.ctx)
        self.window_names = {}
        self.csr_window_names = {}
        self.last_frame = -1
        self.capturing_mouse = True
        glfw.set_cursor_pos_callback(self.window, self.mouse_position_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_key_callback(self.window, self.key_callback)
        glfw.set_window_size_callback(self.window, self.window_size_callback)
        self.timer = time.time()
        if vsync:
            glfw.swap_interval(1)

    def mouse_position_callback(self, window, x, y):
        self.app.user_input_ubo.iMouse[0] = float(x)
        self.app.user_input_ubo.iMouse[1] = float(y)
        frame = self.app.user_output_ubo.hit_level
        if frame != -1:
            self.last_frame = frame
            self.app.user_input_ubo.sel_lvl[0] = frame

    def mouse_button_callback(self, window, button, action, mods):
        if action == glfw.PRESS:
            x, y = glfw.get_cursor_pos(window)
            self.app.user_input_ubo.iMouse[0] = float(x)
            self.app.user_input_ubo.iMouse[1] = float(y)
            frame = self.app.user_output_ubo.hit_level
            if frame != -1:
                self.last_frame = frame
                self.app.user_input_ubo.sel_lvl[0] = frame

    def scroll_callback(self, window, x_offset, y_offset):
        if self.last_frame != -1:
            rect = self.app.input_texture_infos_ubo.tex_levels[self.last_frame]['rect']
            swap = self.app.input_texture_infos_ubo.tex_levels[self.last_frame]['flags'] & 8
            width = self.app.input_texture_infos_ubo.tex_levels[self.last_frame]['width']
            height = self.app.input_texture_infos_ubo.tex_levels[self.last_frame]['height']
            scale_factor = 0.1 * y_offset
            width_adjustment = width * scale_factor
            height_adjustment = height * scale_factor
            if not swap:
                rect[0] -= width_adjustment / 2
                rect[1] -= height_adjustment / 2
                rect[2] += width_adjustment / 2
                rect[3] += height_adjustment / 2
            else:
                rect[0] -= width_adjustment / 2
                rect[1] -= height_adjustment / 2
                rect[2] += width_adjustment / 2
                rect[3] += height_adjustment / 2

    def key_callback(self, window, key, scancode, action, mods):
        if key == glfw.KEY_P and action == glfw.PRESS:
            rects = []
            for i in range(len(self.app.input_texture_infos_ubo.tex_levels)):
                r = self.app.input_texture_infos_ubo.tex_levels[i]['rect']
                rects.append((r[2] - r[0], r[3] - r[1]))
            packer = rectpack.newPacker(
                mode=rectpack.PackingMode.Offline,
                pack_algo=rectpack.MaxRectsBaf,
                bin_algo=rectpack.PackingBin.BFF,
                sort_algo=rectpack.SORT_AREA,
                rotation=False
            )
            width, height = glfw.get_window_size(self.window)
            bins = [(height, width)]
            for i, r in enumerate(rects):
                packer.add_rect(*r, rid=i)
            for b in bins:
                packer.add_bin(*b)
            packer.pack()
            all_rects = packer.rect_list()
            for rect in all_rects:
                b, x, y, w, h, rid = rect
                self.app.input_texture_infos_ubo.tex_levels[rid]['rect'] = [x, y, x + w, y + h]

    def window_size_callback(self, window, width, height):
        self.ctx.viewport = (0, 0, width, height)

    def imshow(self, window_name, frame):
        if frame.dtype in [np.float32, np.float64]:
            frame = (frame * 255).astype(np.uint8)
        elif frame.dtype not in [np.uint8, np.int8]:
            frame = frame.astype(np.uint8)
        if (scipy_available and isinstance(frame, scipy.sparse.csr_matrix)) or \
           (pytorch_available and isinstance(frame, torch.Tensor) and frame.layout == torch.sparse_csr):
            if window_name in self.csr_window_names:
                i = self.csr_window_names[window_name]
                self.app.input_texture_infos_ubo.set_csr_input_stream(i, frame, name=window_name, flags=1)
            else:
                self.csr_window_names[window_name] = self.app.input_texture_infos_ubo.append_csr_input_stream(frame, name=window_name, flags=1)
        else:
            if window_name in self.window_names:
                i = self.window_names[window_name]
                self.app.input_texture_infos_ubo.set_input_stream(i, frame, name=window_name, flags=1)
            else:
                self.window_names[window_name] = self.app.input_texture_infos_ubo.append_input_stream(frame, name=window_name, flags=1)
        self.app.user_input_ubo.sel_lvl[0] = 0  # Force select first image for testing

    def update(self):
        if glfw.window_should_close(self.window):
            glfw.terminate()
            return False
        current_time = time.time()
        delta = current_time - self.timer
        self.timer = current_time
        width, height = glfw.get_window_size(self.window)
        self.app.update(width, height)
        glfw.swap_buffers(self.window)
        glfw.poll_events()
        return True
