import moderngl_window as mgw
import rectpack
import struct
from typing import TYPE_CHECKING, Callable, Optional
if TYPE_CHECKING:  # avoid cyclic imports
    from displayarray.window.mglwindow import UserInputUBO, UserOutputUBO, InputTextureInfosUBO


class MglWindowConfig(mgw.WindowConfig):
    resizable = True
    gl_version = (4, 3)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        mgw.window()
        self.str_buf = None
        self.str_ptr_buf = None
        self.uibo = None
        self.hit_buff = None
        self.rbuf = None
        self.last_frame = -1

    def set_in_buff(self, in_buff: 'UserInputUBO'):
        self.uibo = in_buff

    def set_hit_buff(self, hit_buff: 'UserOutputUBO'):
        self.hit_buff = hit_buff

    def set_rect_buff(self, rect_buff: 'InputTextureInfosUBO'):
        self.rbuf = rect_buff

    def set_text_buff(self, string_buffer, string_ptr_buffer):
        self.str_buf = string_buffer
        self.str_ptr_buf = string_ptr_buffer

    def _update_hit_detection(self, frame):  # todo: use this to clean up duplicated code
        """Update last_frame and sel_lvl from a hit-detection result."""
        if frame != -1:
            self.last_frame = frame
            if self.uibo is not None:
                self.uibo.sel_lvl[0] = frame

    def on_mouse_position_event(self, x, y, dx, dy):
        if self.uibo is not None:
            self.uibo.iMouse[0] = float(x)
            self.uibo.iMouse[1] = float(y)
        if self.hit_buff is not None:
            frame = self.hit_buff.hit_level
            if frame!=-1:
                self.last_frame = frame
                if self.uibo is not None:
                    self.uibo.sel_lvl[0] = frame

    def get_local_mouse_data(self, x, y):
        if self.last_frame == -1 or self.rbuf is None:
            return None

        level_data = self.rbuf.tex_levels[self.last_frame]
        rect = self.rbuf.tex_levels[self.last_frame]['rect']
        orig_w = level_data['width']
        orig_h = level_data['height']
        swap = self.rbuf.tex_levels[self.last_frame]['flags'] & 8

        screen_h = rect[2] - rect[0]
        screen_w = rect[3] - rect[1]

        if screen_w == 0 or screen_h == 0:
            return None

        rel_x_pct = (x - rect[1]) / screen_w
        rel_y_pct = (y - rect[0]) / screen_h

        if swap:
            tex_x_pct = rel_y_pct
            tex_y_pct = rel_x_pct
            current_target_w = orig_h
            current_target_h = orig_w
        else:
            tex_x_pct = rel_x_pct
            tex_y_pct = rel_y_pct
            current_target_w = orig_w
            current_target_h = orig_h

        pixel_x = int(round(tex_x_pct * orig_w))
        pixel_y = int(round(tex_y_pct * orig_h))

        return pixel_x, pixel_y, float(tex_x_pct), float(tex_y_pct)

    def on_mouse_scroll_event(self, x_offset: float, y_offset: float):
        if self.hit_buff is not None:
            rect = self.rbuf.tex_levels[self.last_frame]['rect']
            swap = self.rbuf.tex_levels[self.last_frame]['flags']&8

            # Calculate current width and height of the rectangle
            width = self.rbuf.tex_levels[self.last_frame]['width']
            height = self.rbuf.tex_levels[self.last_frame]['height']

            # Calculate scale factor (for example, 1% per scroll unit)
            scale_factor = 0.1 * y_offset

            # Calculate adjustment based on scale factor
            width_adjustment = width * scale_factor
            height_adjustment = height * scale_factor

            if not swap:
                # Adjust the top-left and bottom-right corners
                rect[0] -= width_adjustment / 2  # Left
                rect[1] -= height_adjustment / 2  # Top
                rect[2] += width_adjustment / 2  # Right
                rect[3] += height_adjustment / 2  # Bottom
            else:
                # Adjust the top-left and bottom-right corners
                rect[0] -= width_adjustment / 2  # Left
                rect[1] -= height_adjustment / 2  # Top
                rect[2] += width_adjustment / 2  # Right
                rect[3] += height_adjustment / 2  # Bottom

    def on_mouse_press_event(self, x, y, button):
        # sometimes mouse position event doesn't always trigger, so clicking can now help
        if self.uibo is not None:
            self.uibo.iMouse[0] = float(x)
            self.uibo.iMouse[1] = float(y)
        if self.hit_buff is not None:
            frame = self.hit_buff.hit_level
            if frame != -1:
                self.last_frame = frame
                if self.uibo is not None:
                    self.uibo.sel_lvl[0] = frame

    def on_mouse_drag_event(self, x: int, y: int, dx: int, dy: int):
        if self.hit_buff is not None:
            rect = self.rbuf.tex_levels[self.last_frame]['rect']
            swap = self.rbuf.tex_levels[self.last_frame]['flags']&8
            if not swap:
                rect[0] += dx
                rect[1] += dy
                rect[2] += dx
                rect[3] += dy
            else:
                rect[0] += dy
                rect[1] += dx
                rect[2] += dy
                rect[3] += dx

    def on_key_event(self, key, action, modifiers):
        if key == self.wnd.keys.P and action == self.wnd.keys.ACTION_PRESS:
            if self.rbuf is None:
                return
            rects = []
            for i in range(len(self.rbuf.tex_levels)):
                r = self.rbuf.tex_levels[i]['rect']  #ltrb
                rects.append((r[2]-r[0], r[3]-r[1]))
            packer = rectpack.newPacker(
                mode=rectpack.PackingMode.Offline,
                pack_algo=rectpack.MaxRectsBaf,
                bin_algo=rectpack.PackingBin.BFF,
                sort_algo=rectpack.SORT_AREA,
                rotation=False
            )

            bins = [(self.wnd.height, self.wnd.width)]

            for i,r in enumerate(rects):
                packer.add_rect(*r, rid=i)

            # Add the bins where the rectangles will be placed
            for b in bins:
                packer.add_bin(*b)

            # Start packing
            packer.pack()

            all_rects = packer.rect_list()
            for rect in all_rects:
                b, x, y, w, h, rid = rect
                self.rbuf.tex_levels[rid]['rect'][0] = x
                self.rbuf.tex_levels[rid]['rect'][1] = y
                self.rbuf.tex_levels[rid]['rect'][2] = x+w
                self.rbuf.tex_levels[rid]['rect'][3] = y + h


class PassthruMglWindowConfig(MglWindowConfig):
    """
    MglWindowConfig with three switchable input modes.

    Mode 0  Default      Base class behaviour (drag, zoom, P-pack).
    Mode 1  Pass-through Route all input to pass_through_cb.
    Mode 2  Edit         Route all input to edit_cb.

    Switch modes with Ctrl+Shift+0 / 1 / 2.

    Instantiate via the factory so moderngl_window receives an uninitialised class:
        cfg = PassthruMglWindowConfig.with_callbacks(pass_through_cb, edit_cb)

    Callback signature:
        cb(event_type: str, frame: int, name: str | None, *event_args)

    event_type / event_args:
        'mouse_pos'    px, py, tex_x, tex_y, screen_x, screen_y
        'mouse_press'  screen_x, screen_y, button
        'mouse_scroll' x_offset, y_offset
        'mouse_drag'   screen_x, screen_y, dx, dy
        'key'          key, action, modifiers
    """

    pass_through_cb: Optional[Callable] = None
    edit_cb:         Optional[Callable] = None

    @classmethod
    def with_callbacks(cls,
                       pass_through_cb: Optional[Callable] = None,
                       edit_cb:         Optional[Callable] = None):
        class _Configured(cls):
            pass
        _Configured.pass_through_cb = staticmethod(pass_through_cb) if pass_through_cb else None
        _Configured.edit_cb         = staticmethod(edit_cb)         if edit_cb         else None
        return _Configured

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_mode = 0   # 0=default  1=pass-through  2=edit

    def get_target_name(self, index: int) -> Optional[str]:
        if self.str_buf is None or self.str_ptr_buf is None or index < 0:
            return None
        try:
            n = struct.unpack('<i', self.str_ptr_buf.read(size=4, offset=0))[0]
            if index >= n:
                return None
            start, end = struct.unpack('<2i',
                self.str_ptr_buf.read(size=8, offset=4 + index * 4))
            length = end - start
            if length <= 0:
                return ''
            chars = struct.unpack(f'<{length}i',
                self.str_buf.read(size=length * 4, offset=start * 4))
            return ''.join(chr(c) for c in chars)
        except Exception as exc:
            print(f'[PassthruMglWindowConfig] get_target_name: {exc}')
            return None

    def get_local_mouse_data(self, x, y, clamp=False):
        """
        Extends base with optional rect-clamping.
        Returns (pixel_x, pixel_y, tex_x, tex_y, screen_x, screen_y).
        """
        if self.last_frame == -1 or self.rbuf is None:
            return None
        rect = self.rbuf.tex_levels[self.last_frame]['rect']
        if clamp:
            x = max(rect[0], min(x, rect[2]))
            y = max(rect[1], min(y, rect[3]))
        result = super().get_local_mouse_data(x, y)
        if result is None:
            return None
        px, py, tx, ty = result
        return px, py, tx, ty, x, y

    def _route(self, event_type, *args) -> bool:
        """Dispatch to the active mode's callback. Returns True if consumed."""
        cb = (self.pass_through_cb if self.input_mode == 1 else
              self.edit_cb         if self.input_mode == 2 else None)
        if cb:
            cb(event_type, self.last_frame, self.get_target_name(self.last_frame), *args)
            return True
        return False

    def on_mouse_position_event(self, x, y, dx, dy):
        if self.hit_buff is not None:
            self._update_hit_detection(self.hit_buff.hit_level)
        if self.input_mode in (1, 2):
            local = self.get_local_mouse_data(x, y, clamp=(self.input_mode == 1))
            if local:
                self._route('mouse_pos', *local)
        else:
            if self.uibo is not None:
                self.uibo.iMouse[0] = float(x)
                self.uibo.iMouse[1] = float(y)

    def on_mouse_scroll_event(self, x_offset: float, y_offset: float):
        if not self._route('mouse_scroll', x_offset, y_offset):
            super().on_mouse_scroll_event(x_offset, y_offset)

    def on_mouse_press_event(self, x, y, button):
        if not self._route('mouse_press', x, y, button):
            super().on_mouse_press_event(x, y, button)

    def on_mouse_release_event(self, x: int, y: int, button: int) -> None:
        if not self._route('mouse_release', x, y, button):
            super().on_mouse_release_event(x, y, button)

    def on_mouse_drag_event(self, x: int, y: int, dx: int, dy: int):
        if not self._route('mouse_drag', x, y, dx, dy):
            super().on_mouse_drag_event(x, y, dx, dy)

    def on_key_event(self, key, action, modifiers):
        keys = self.wnd.keys
        #print(modifiers)
        #print(action)
        #print(key)
        if modifiers.ctrl and modifiers.shift and action == keys.ACTION_PRESS:
            #print('in')
            '''mode_map = {
                keys.NUMBER_0: (0, 'Default'),
                keys.NUMBER_1: (1, 'Pass-through'),
                keys.NUMBER_2: (2, 'Edit'),
            }'''
            mode_map = {  # Different key codes when pressing ctrl+shift+num
                41: (0, 'Default'),
                33: (1, 'Pass-through'),
                64: (2, 'Edit'),
            }
            if key in mode_map:
                self.input_mode, label = mode_map[key]
                print(f'[window] mode {self.input_mode}: {label}')
                return
        if not self._route('key', key, action, modifiers):
            super().on_key_event(key, action, modifiers)