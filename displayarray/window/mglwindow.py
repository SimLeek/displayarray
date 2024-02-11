import numpy as np
import moderngl_window as mgw
import moderngl as mgl
import cv2
import struct
from moderngl_window import geometry
import os

dir_path = os.path.dirname(os.path.realpath(__file__))


class MglWindowConfig(mgw.WindowConfig):
    resizable = True
    gl_version = (4, 3)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        mgw.window()
        self.uibo = None
        self.hit_buff = None
        self.rbuf = None
        self.last_frame = -1

    '''def key_event(self, key, action, modifiers):
        """Events for one time key presses, like pause"""
        if key == 256:  # pygame.K_ESCAPE
            self.capturing_mouse = not self.capturing_mouse'''

    def set_in_buff(self, in_buff: 'UserInputUBO'):
        self.uibo = in_buff

    def set_hit_buff(self, hit_buff: 'UserOutputUBO'):
        self.hit_buff = hit_buff
    def set_rect_buff(self, rect_buff: 'InputTextureInfosUBO'):
        self.rbuf = rect_buff
    def mouse_position_event(self, x, y, dx, dy):
        if self.uibo is not None:
            self.uibo.iMouse[0] = float(x)
            self.uibo.iMouse[1] = float(y)

    def mouse_drag_event(self, x: int, y: int, dx: int, dy: int):
        if self.hit_buff is not None:
            frame = self.hit_buff.hit_level
            if frame!=-1:
                self.last_frame = frame
            rect = self.rbuf.tex_levels[self.last_frame]['rect']
            rect[0] += dx
            rect[1] += dy
            rect[2] += dx
            rect[3] += dy





def create_no_input_texture(width=100, height=100):
    # Create a black image
    img = np.zeros((height, width, 3), np.uint8)

    # Write "no input" text in the middle
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = "No Input"
    text_size = cv2.getTextSize(text, font, 1, 2)[0]
    text_x = (width - text_size[0]) // 2
    text_y = (height + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

    return img


class InputTextureInfosUBO(object):
    def __init__(self, start_textures=[]):
        self.channels = 3  # Assuming RGB format
        self.tex_levels = []
        self.input_image: np.ndarray = np.asarray([], dtype=np.float32)
        self.no_input = not bool(start_textures)

        # Initialize input image buffer with a default "no input" image
        if not start_textures:
            start_textures = [create_no_input_texture()]

        # Initialize texture levels with default values
        for s in start_textures:
            tex_level = {'startIdx': 0, 'width': s.shape[0], 'height': s.shape[1], 'rect': [1.0, 0.0, 0.0, 1.0]}
            self.tex_levels.append(tex_level)
            self.input_image = np.concatenate((self.input_image, s.flatten()), axis=0, dtype=self.input_image.dtype)

    def append_input_stream(self, img:np.ndarray):
        i = len(self.tex_levels)
        start_index = self.tex_levels[-1]['startIdx']+\
                      self.tex_levels[-1]['width']*self.tex_levels[-1]['height']*self.channels
        width = img.shape[0]
        height = img.shape[1]
        assert img.shape[2] == self.channels
        rect = [0,0,width,height]
        self.tex_levels.append({
            'startIdx': start_index,
            'width': width,
            'height': height,
            'rect': rect
        })
        self.input_image = np.concatenate((self.input_image, img.flatten()), axis=0, dtype=self.input_image.dtype)
        #self.input_image[start_index:] =  img.flatten()

        return i

    def set_input_stream(self, i, img:np.ndarray):
        start_index = self.tex_levels[i]['startIdx']
        end_index = start_index + img.shape[0] * img.shape[1] * self.channels
        assert img.shape[2] == self.channels
        if i!=len(self.tex_levels) and \
            self.tex_levels[i]['width']*self.tex_levels[i]['height']!=img.shape[0]*img.shape[1]:
            ind = start_index
            for j in range(i, len(self.tex_levels)):
                new_start_index = ind + img.shape[0]*img.shape[1]*self.channels
                self.tex_levels[j]['startIdx'] = new_start_index
                ind = new_start_index

        self.tex_levels[i]['width'] = img.shape[0]
        self.tex_levels[i]['height'] = img.shape[1]

        self.input_image[start_index:end_index] = img.flatten()

    def get_tex_data_buffer(self):
        tex_data_bytes = bytearray()
        tex_data_bytes.extend(struct.pack("<2ixxxxxxxx", self.channels, len(self.tex_levels)))
        for level in self.tex_levels:
            tex_data_bytes.extend(struct.pack("<3ixxxx", level['startIdx'], level['width'], level['height']))
            tex_data_bytes.extend(struct.pack("<4f", *level['rect']))
        return bytes(tex_data_bytes)

    def set_tex_data_buffer(self, data):
        if len(data) - 2 % 7 != 0:
            raise ValueError("Input data size does not match buffer format")
        self.channels = data[0]
        num_levels = data[1]
        for i in range(num_levels):
            self.tex_levels[i]['startIdx'] = data[i * 7 + 2]
            self.tex_levels[i]['width'] = data[i * 7 + 3]
            self.tex_levels[i]['height'] = data[i * 7 + 4]
            self.tex_levels[i]['rect'] = data[i * 7 + 5:i * 7 + 9]

    def append_tex_data_buffer(self, data):
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

    def get_input_image_buffer(self):
        return self.input_image.tobytes()

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
        self.iMouse = np.zeros((2,), np.float32)

    def to_bytes(self):
        return struct.pack(f"<ff",
                           *self.iMouse)

    @property
    def nbytes(self):
        return len(self.to_bytes())

class UserOutputUBO:
    def __init__(self):
        self.hit_level = -1
        self.hit_pos = (-1.0, -1.0)

    def to_bytes(self):
        return struct.pack(f"<ixxxxff",
                           self.hit_level, *self.hit_pos)

    @property
    def nbytes(self):
        return len(self.to_bytes())


class MglApp(object):
    def __init__(self, ctx: mgl.Context):
        self.user_input_ubo_buffer = None
        self.user_output_ubo_buffer = None
        self.input_texture_ubo_buffer = None
        self.input_texture_infos_ubo_buffer = None
        self.ctx = ctx
        self.input_texture_infos_ubo = InputTextureInfosUBO()
        self.user_input_ubo = UserInputUBO()
        self.user_output_ubo = UserOutputUBO()
        self.capturing_mouse = True


        self.quad_fs = geometry.quad_fs()

        # Initialize uniform buffers and shaders
        self.create_shaders()

    def create_shaders(self):
        # Compile shaders
        self.vertex_shader = """
            #version 430
            in vec2 in_position;
            in vec4 in_texcoord_0;

            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
            }
        """
        self.fragment_shader = None
        with open(dir_path + os.sep + "pyr_quads.frag") as f:
            self.fragment_shader = f.read()

        self.shader = self.ctx.program(vertex_shader=self.vertex_shader, fragment_shader=self.fragment_shader)

        self.input_texture_ubo_buffer = self.ctx.buffer(reserve=4*1920*1080*2*3, dynamic=True)
        self.input_texture_infos_ubo_buffer = self.ctx.buffer(reserve=4*30*7+4*2, dynamic=True)
        self.user_input_ubo_buffer = self.ctx.buffer(self.user_input_ubo.to_bytes(), dynamic=False)
        self.user_output_ubo_buffer = self.ctx.buffer(self.user_output_ubo.to_bytes(), dynamic=False)

        self.input_texture_ubo_buffer.bind_to_storage_buffer(0)
        self.input_texture_infos_ubo_buffer.bind_to_storage_buffer(1)
        self.user_input_ubo_buffer.bind_to_storage_buffer(2)
        self.user_output_ubo_buffer.bind_to_storage_buffer(3)

        self.update_buffers()

    def update_buffers(self):
        # Update uniform buffers
        self.input_texture_ubo_buffer.write(self.input_texture_infos_ubo.get_input_image_buffer())
        self.input_texture_infos_ubo_buffer.write(self.input_texture_infos_ubo.get_tex_data_buffer())
        self.user_input_ubo_buffer.write(self.user_input_ubo.to_bytes())
        out_data = self.user_output_ubo_buffer.read()
        int_list = []
        for i in range(len(out_data)//4):
            int_list.append(int.from_bytes(out_data[i*4:(i+1)*4], byteorder='little', signed=True))
        self.user_output_ubo.hit_level = int.from_bytes(out_data[0:4], byteorder='little', signed=True)
        self.user_output_ubo.hit_pos = np.frombuffer(out_data[4:], dtype=np.float32)
        #if self.user_output_ubo.hit_level!=-1:
        #    print(f"hit: {self.user_output_ubo.hit_level}")
        #    print(f"x,y: {self.user_output_ubo.hit_pos}")


        #self.shader['InputBuffer'].write(self.input_texture_infos_ubo.get_input_image_buffer())
        #self.shader['TexData'].write(self.input_texture_infos_ubo.get_tex_data_buffer())
        #self.shader['UserInput'].write(self.user_input_ubo.to_bytes())

    def update(self, time, frame_time):
        # self.ctx.clear(1.0, 1.0, 1.0)
        # Render the quad using shaders
        self.update_buffers()
        self.quad_fs.render(self.shader)


class MglWindow(object):
    def __init__(self, timer=None, args=None, backend="pygame2"):
        if backend is not None:
            available = mgw.find_window_classes()
            assert backend in available, f"backend {backend} is not installed. Installed backends: {available}"

        config_cls = MglWindowConfig
        mgw.setup_basic_logging(config_cls.log_level)
        parser = mgw.create_parser()
        config_cls.add_arguments(parser)
        values = mgw.parse_args(args=args, parser=parser)
        config_cls.argv = values
        window_cls = mgw.get_local_window_cls(backend)

        # Calculate window size
        size = values.size or config_cls.window_size
        size = int(size[0] * values.size_mult), int(size[1] * values.size_mult)

        # Resolve cursor
        show_cursor = values.cursor
        if show_cursor is None:
            show_cursor = config_cls.cursor

        self.window = window_cls(
            title=config_cls.title,
            size=size,
            fullscreen=config_cls.fullscreen or values.fullscreen,
            resizable=values.resizable
            if values.resizable is not None
            else config_cls.resizable,
            gl_version=config_cls.gl_version,
            aspect_ratio=config_cls.aspect_ratio,
            vsync=values.vsync if values.vsync is not None else config_cls.vsync,
            samples=values.samples if values.samples is not None else config_cls.samples,
            cursor=show_cursor if show_cursor is not None else True,
            backend=None,
        )
        self.window.print_context_info()
        mgw.activate_context(window=self.window)
        self.timer = timer or mgw.Timer()
        self.config = config_cls(ctx=self.window.ctx, wnd=self.window, timer=self.timer)
        # Avoid the event assigning in the property setter for now
        # We want the even assigning to happen in WindowConfig.__init__
        # so users are free to assign them in their own __init__.
        self.window._config = mgw.weakref.ref(self.config)

        # Swap buffers once before staring the main loop.
        # This can trigged additional resize events reporting
        # a more accurate buffer size
        self.window.swap_buffers()
        self.window.set_default_viewport()

        self.app = MglApp(self.window.ctx)
        self.config.set_in_buff(self.app.user_input_ubo)
        self.config.set_hit_buff(self.app.user_output_ubo)
        self.config.set_rect_buff(self.app.input_texture_infos_ubo)
        self.window.render_func = self.app.update

        self.timer.start()

        self.counter = 0
        self.window_names = {}

    def imshow(self, window_name, frame):
        frame = np.swapaxes(frame, 0, 1)
        frame[:,:, [2, 0]] = frame[:,:, [0, 2]]

        if frame.dtype == np.uint8:
            frame = frame.astype(np.float32) / 255

        if window_name in self.window_names.keys():
            i = self.window_names[window_name]
            self.app.input_texture_infos_ubo.set_input_stream(i, frame)
        else:
            self.window_names[window_name] = self.app.input_texture_infos_ubo.append_input_stream(frame)

    def update(self):
        current_time, delta = self.timer.next_frame()

        if self.config.clear_color is not None:
            self.window.clear(*self.config.clear_color)

        # Always bind the window framebuffer before calling render
        self.window.use()

        self.window.render(current_time, delta)
        if not self.window.is_closing:
            self.window.swap_buffers()
        else:
            _, duration = self.timer.stop()
            self.window.destroy()
