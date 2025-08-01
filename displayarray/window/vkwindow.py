import numpy as np
import vulkan as vk
import glfw
import cv2
import struct
import os
from rectpack import newPacker, PackingMode, PackingBin, MaxRectsBaf, SORT_AREA
from displayarray.font.get_texture_atlas import get_or_create_font_npz
from typing import Union
import subprocess
import sys
from ctypes import c_void_p, c_uint64, byref, CFUNCTYPE, c_int, c_uint32, addressof, memmove
import ctypes
import cffi
ffi = cffi.FFI()

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

# Function prototypes for Vulkan extension functions
VK_GET_PHYSICAL_DEVICE_SURFACE_CAPABILITIES_KHR = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)
VK_GET_PHYSICAL_DEVICE_SURFACE_FORMATS_KHR = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, c_void_p)
VK_DESTROY_SURFACE_KHR = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)
VK_DESTROY_SWAPCHAIN_KHR = CFUNCTYPE(None, c_void_p, c_void_p, c_void_p)
VK_CREATE_SWAPCHAIN_KHR = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, c_void_p)
VK_GET_SWAPCHAIN_IMAGES_KHR = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p, c_void_p)
VK_ACQUIRE_NEXT_IMAGE_KHR = CFUNCTYPE(c_int, c_void_p, c_uint64, c_uint64, c_uint64, c_uint64, c_void_p)
VK_QUEUE_PRESENT_KHR = CFUNCTYPE(c_int, c_void_p, c_void_p)

class InstanceProcAddr:
    T = None  # Will be set to instance handle

    def __init__(self, func_name):
        self.func_name = func_name
        self.func = None

    def __call__(self, *args):
        if self.func is None:
            self.func = vk.vkGetInstanceProcAddr(self.T, self.func_name)
            if not self.func:
                raise RuntimeError(f"Failed to load {self.func_name}")
        return self.func(*args)

class DeviceProcAddr(InstanceProcAddr):
    def __call__(self, *args):
        if self.func is None:
            self.func = vk.vkGetDeviceProcAddr(self.T, self.func_name)
            if not self.func:
                raise RuntimeError(f"Failed to load {self.func_name}")
        return self.func(*args)

# Define extension functions
vkGetPhysicalDeviceSurfaceCapabilitiesKHR = InstanceProcAddr("vkGetPhysicalDeviceSurfaceCapabilitiesKHR")
vkGetPhysicalDeviceSurfaceFormatsKHR = InstanceProcAddr("vkGetPhysicalDeviceSurfaceFormatsKHR")
vkDestroySurfaceKHR = InstanceProcAddr("vkDestroySurfaceKHR")
vkDestroySwapchainKHR = DeviceProcAddr("vkDestroySwapchainKHR")
vkCreateSwapchainKHR = DeviceProcAddr("vkCreateSwapchainKHR")
vkGetSwapchainImagesKHR = DeviceProcAddr("vkGetSwapchainImagesKHR")
vkAcquireNextImageKHR = DeviceProcAddr("vkAcquireNextImageKHR")
vkQueuePresentKHR = DeviceProcAddr("vkQueuePresentKHR")
vkCreateDebugUtilsMessengerEXT = InstanceProcAddr("vkCreateDebugUtilsMessengerEXT")


def get_shader(filename):
    if filename.endswith('.glsl') or filename.endswith('.vert') or filename.endswith('.frag'):
        spv_filename = filename[:-5] + '.spv'
        if not os.path.exists(spv_filename):
            try:
                subprocess.run(["glslc", filename, "-o", spv_filename],
                              check=True,
                              stdout=sys.stdout,
                              stderr=sys.stderr, text=True)
            except subprocess.CalledProcessError as e:
                print("glslc command failed with output:")
                print(e.stdout)
                print(e.stderr, file=sys.stderr)
                raise e
        with open(spv_filename, 'rb') as f:
            shader = f.read()
    else:
        raise ValueError("Invalid file extension. Filename must end with .glsl, .vert, or .frag")
    return shader

class InputTextureInfosUBO:
    def __init__(self, start_textures=[]):
        self.channels = 3
        self.tex_levels = []
        self.input_image = []
        self.names = []
        self.no_input = not bool(start_textures)

    def append_input_stream(self, img: np.ndarray, name="Unnamed", flags: int=0):
        i = len(self.tex_levels)
        start_index = 0 if i == 0 else (self.tex_levels[-1]['startIdx'] +
                                        self.tex_levels[-1]['width'] * self.tex_levels[-1]['height'] * self.tex_levels[-1]['channels'])
        width = img.shape[1]
        height = img.shape[0]
        channels = 1 if len(img.shape) == 2 else img.shape[2]
        rect = [0, 0, width, height]
        self.tex_levels.append({
            'startIdx': start_index,
            'width': width,
            'height': height,
            'flags': flags,
            'channels': channels,
            'rect': rect
        })
        self.input_image.append((img, start_index))
        self.names.append(name)
        return i

    def set_input_stream(self, i, img: np.ndarray, name=None, flags: int=0):
        start_index = self.tex_levels[i]['startIdx']
        channels = 1 if len(img.shape) == 2 else img.shape[2]
        if i != len(self.tex_levels) and \
           self.tex_levels[i]['width'] * self.tex_levels[i]['height'] != img.shape[1] * img.shape[0]:
            ind = start_index
            for j in range(i, len(self.tex_levels)):
                new_start_index = ind + img.shape[1] * img.shape[0] * channels
                self.tex_levels[j]['startIdx'] = new_start_index
                ind = new_start_index
        self.tex_levels[i]['width'] = img.shape[1]
        self.tex_levels[i]['height'] = img.shape[0]
        self.tex_levels[i]['flags'] = flags
        self.tex_levels[i]['channels'] = channels
        if name is not None:
            self.names[i] = name
        else:
            self.names[i] = f"Unnamed {i}"
        self.input_image[i] = (img, start_index)

    def append_csr_input_stream(self, img: SparseType, name="Unnamed", flags: int=0):
        i = len(self.tex_levels)
        start_index = 0 if i == 0 else (self.tex_levels[-1]['startIdx'] +
                                        self.tex_levels[-1]['width'] * self.tex_levels[-1]['height'] * self.tex_levels[-1]['channels'])
        width = img.shape[1]
        height = img.shape[0]
        channels = 1 if len(img.shape) == 2 else img.shape[2]
        rect = [0, 0, width, height]
        self.tex_levels.append({
            'startIdx': start_index,
            'width': width,
            'height': height,
            'flags': flags,
            'channels': channels,
            'rect': rect
        })
        self.input_image.append((img, start_index))
        self.names.append(name)
        return i

    def set_csr_input_stream(self, i, img: SparseType, name=None, flags: int=0):
        start_index = self.tex_levels[i]['startIdx']
        channels = 1 if len(img.shape) == 2 else img.shape[2]
        if i != len(self.tex_levels) and \
           self.tex_levels[i]['width'] * self.tex_levels[i]['height'] != img.shape[1] * img.shape[0]:
            ind = start_index
            for j in range(i, len(self.tex_levels)):
                new_start_index = ind + img.shape[1] * img.shape[0] * channels
                self.tex_levels[j]['startIdx'] = new_start_index
                ind = new_start_index
        self.tex_levels[i]['width'] = img.shape[1]
        self.tex_levels[i]['height'] = img.shape[0]
        self.tex_levels[i]['flags'] = flags
        self.tex_levels[i]['channels'] = channels
        if name is not None:
            self.names[i] = name
        else:
            self.names[i] = f"Unnamed {i}"
        self.input_image[i] = (img, start_index)

    def get_name_str_buffers(self, start_index=0, num_strings=None):
        name_bytes = bytearray()
        name_ptr_bytes = bytearray()
        if start_index == 0:
            name_ptr_bytes.extend(struct.pack("<1i", len(self.names) if num_strings is None else num_strings))
        name_ptrs = [start_index]
        for name in self.names:
            name_ptrs.append(name_ptrs[-1] + len(name))
        if len(name_ptrs) % 4 != 0:
            name_ptrs.extend([name_ptrs[-1]] * int(-len(name_ptrs) % 4))
        name_ptr_bytes.extend(struct.pack(f"<{len(name_ptrs)}i", *name_ptrs))
        for name in self.names:
            name_bytes.extend(struct.pack(f"<{len(name)}i", *[ord(n) for n in name]))
        return name_bytes, name_ptr_bytes

    def get_tex_data_buffer(self):
        tex_data_bytes = bytearray()
        tex_data_bytes.extend(struct.pack("<1i", len(self.tex_levels)))
        for level in self.tex_levels:
            tex_data_bytes.extend(struct.pack("<5i", level['startIdx'], level['width'], level['height'], level['flags'], level['channels']))
            tex_data_bytes.extend(struct.pack("<4f", *level['rect']))
        return bytes(tex_data_bytes)

    def get_input_image_buffer(self, writer, device, queue, buffer):
        for t in self.input_image:
            img, start = t
            if isinstance(img, np.ndarray):
                data = img.tobytes()
            else:  # Sparse matrix
                data = img.toarray().tobytes()
            writer(data, offset=start * 4, device=device, queue=queue, buffer=buffer)

class UserInputUBO:
    def __init__(self):
        self.sel_lvl = np.zeros((1), np.int32)
        self.iMouse = np.zeros((2,), np.float32)

    def to_bytes(self):
        return struct.pack(f"<ixxxxff", *self.sel_lvl, *self.iMouse)

class UserOutputUBO:
    def __init__(self):
        self.hit_level = -1
        self.hit_pos = (-1.0, -1.0)

    def to_bytes(self):
        return struct.pack(f"<ixxxxff", self.hit_level, *self.hit_pos)

class VulkanApp:
    def __init__(self, window):
        self.window = window
        self.user_input_ubo = UserInputUBO()
        self.user_output_ubo = UserOutputUBO()
        self.input_texture_infos_ubo = InputTextureInfosUBO()
        self.capturing_mouse = True
        self.last_frame = -1
        self.needs_resize = False  # Flag to track resize events
        self.swapchain_extent = None

        # Set GLFW window size callback
        def window_size_callback(window, width, height):
            self.needs_resize = True

        glfw.set_window_size_callback(self.window, window_size_callback)

        # Vulkan initialization
        if not glfw.vulkan_supported():
            raise RuntimeError("Vulkan is not supported")
        self.instance = self.create_instance()

        '''PFN_vkDebugUtilsMessengerCallbackEXT = ctypes.CFUNCTYPE(
            vk.VkBool32,
            vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT,
            vk.VkDebugUtilsMessageTypeFlagsEXT,
            ctypes.POINTER(vk.VkDebugUtilsMessengerCallbackDataEXT),
            ctypes.c_void_p
        )'''
        #debug extensions don't exist on this system
        '''def debug_callback(severity, type, callback_data, user_data):
            msg = callback_data.contents.pMessage.decode()
            print(f"[VK DEBUG] {msg}")
            return vk.VK_FALSE
        debug_create_info = vk.VkDebugUtilsMessengerCreateInfoEXT(
            sType=vk.VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
            messageSeverity=vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                            vk.VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
            messageType=vk.VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                        vk.VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                        vk.VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT,
            pfnUserCallback=debug_callback
        )
        #self.debug_messenger = vk.DebugUtilsMessen(0)
        vkCreateDebugUtilsMessengerEXT(debug_create_info, None, None)'''

        InstanceProcAddr.T = self.instance  # Set instance for dynamic loading
        self.physical_device, self.device, self.queue, self.queue_family_index = self.create_device()
        DeviceProcAddr.T = self.device  # Set device for dynamic loading
        self.swapchain, self.swapchain_images, self.swapchain_image_views = self.create_swapchain()
        self.render_pass = self.create_render_pass()
        self.framebuffers = self.create_framebuffers()
        self.command_pool, self.command_buffers = self.create_command_buffers()
        self.pipeline, self.pipeline_layout, self.shader_modules = self.create_pipeline()
        self.buffers = self.create_buffers()
        npz_data = np.load(get_or_create_font_npz(), allow_pickle=True)
        self.load_font_atlas(npz_data)
        self.descriptor_pool, self.descriptor_sets = self.create_descriptor_sets()
        self.semaphore_image_available = vk.vkCreateSemaphore(self.device, vk.VkSemaphoreCreateInfo(), None)
        self.semaphore_render_finished = vk.vkCreateSemaphore(self.device, vk.VkSemaphoreCreateInfo(), None)
        self.fence = vk.vkCreateFence(self.device, vk.VkFenceCreateInfo(flags=vk.VK_FENCE_CREATE_SIGNALED_BIT), None)

    def create_instance(self):
        app_info = vk.VkApplicationInfo(
            pApplicationName="Vulkan App",
            applicationVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            pEngineName="No Engine",
            engineVersion=vk.VK_MAKE_VERSION(1, 0, 0),
            apiVersion=vk.VK_API_VERSION_1_0
        )
        extensions = glfw.get_required_instance_extensions()
        '''extensions.extend(
            [
                b'VK_KHR_surface',
                b'VK_KHR_xcb_surface',  # or win32/surface_metal/etc.
                b'VK_EXT_debug_utils'
            ]
        )'''
        enabled_layers = []
        layer_info_list = list(vk.vkEnumerateInstanceLayerProperties())

        # no validation layers on the current system. This does work though.
        '''for layer_name in layer_info_list:
            #print(layer_name.layerName, layer_name.description)
            print(layer_name.layerName)
            if 'validation' in layer_name.layerName:
                enabled_layers.append(layer_name)'''

        instance_create_info = vk.VkInstanceCreateInfo(
            pApplicationInfo=app_info,
            enabledLayerCount=len(enabled_layers),
            ppEnabledLayerNames=enabled_layers,
            enabledExtensionCount=len(extensions),
            ppEnabledExtensionNames=extensions
        )

        return vk.vkCreateInstance(instance_create_info, None)

    def create_device(self):
        physical_devices = vk.vkEnumeratePhysicalDevices(self.instance)
        physical_device = physical_devices[0]
        queue_family_properties = vk.vkGetPhysicalDeviceQueueFamilyProperties(physical_device)
        queue_family_index = next(i for i, q in enumerate(queue_family_properties)
                                 if q.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT)
        queue_create_info = vk.VkDeviceQueueCreateInfo(
            queueFamilyIndex=queue_family_index,
            queueCount=1,
            pQueuePriorities=[1.0]
        )
        device_create_info = vk.VkDeviceCreateInfo(
            queueCreateInfoCount=1,
            pQueueCreateInfos=[queue_create_info],
            enabledExtensionCount=1,
            ppEnabledExtensionNames=[vk.VK_KHR_SWAPCHAIN_EXTENSION_NAME]
        )
        device = vk.vkCreateDevice(physical_device, device_create_info, None)
        queue = vk.vkGetDeviceQueue(device, queue_family_index, 0)
        return physical_device, device, queue, queue_family_index

    def create_command_buffers(self):
        command_pool_create_info = vk.VkCommandPoolCreateInfo(
            queueFamilyIndex=self.queue_family_index,
            flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
        )
        command_pool = vk.vkCreateCommandPool(self.device, command_pool_create_info, None)
        command_buffer_allocate_info = vk.VkCommandBufferAllocateInfo(
            commandPool=command_pool,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=len(self.swapchain_images)
        )
        command_buffers = vk.vkAllocateCommandBuffers(self.device, command_buffer_allocate_info)
        return command_pool, command_buffers

    def create_swapchain(self):
        surface = c_uint64()
        result = glfw.create_window_surface(self.instance, self.window, None, byref(surface))
        if result != vk.VK_SUCCESS:
            raise RuntimeError(f"Failed to create window surface: {result}")
        self.surface = surface.value
        capabilities = vk.VkSurfaceCapabilitiesKHR()
        capabilities = vkGetPhysicalDeviceSurfaceCapabilitiesKHR(self.physical_device, self.surface, capabilities)
        self.swapchain_extent = capabilities.currentExtent
        format_count = c_uint32(0)
        formats = vkGetPhysicalDeviceSurfaceFormatsKHR(self.physical_device, self.surface)
        if not formats:
            raise RuntimeError("No surface formats available")
        format = next((f.format for f in formats if
                       f.format == vk.VK_FORMAT_B8G8R8A8_UNORM and f.colorSpace == vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR),
                      formats[0].format)
        swapchain_create_info = vk.VkSwapchainCreateInfoKHR(
            surface=self.surface,
            minImageCount=capabilities.minImageCount + 1,
            imageFormat=format,
            imageColorSpace=vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR,
            imageExtent=capabilities.currentExtent,
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            preTransform=capabilities.currentTransform,
            compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            presentMode=vk.VK_PRESENT_MODE_FIFO_KHR,
            clipped=True
        )
        swapchain = vkCreateSwapchainKHR(self.device, swapchain_create_info, None, None)
        self.swapchain = swapchain
        images = vkGetSwapchainImagesKHR(self.device, self.swapchain)
        image_views = []
        for image in images:
            image_view_create_info = vk.VkImageViewCreateInfo(
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=format,
                components=vk.VkComponentMapping(r=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 g=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 b=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 a=vk.VK_COMPONENT_SWIZZLE_IDENTITY),
                subresourceRange=vk.VkImageSubresourceRange(aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                                                            baseMipLevel=0, levelCount=1,
                                                            baseArrayLayer=0, layerCount=1)
            )
            image_views.append(vk.vkCreateImageView(self.device, image_view_create_info, None))
        return swapchain, images, image_views

    def recreate_swapchain(self):
        vk.vkDeviceWaitIdle(self.device)
        # Clean up old resources
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        for image_view in self.swapchain_image_views:
            vk.vkDestroyImageView(self.device, image_view, None)
        vkDestroySwapchainKHR(self.device, self.swapchain, None)
        # Recreate swapchain
        capabilities = vk.VkSurfaceCapabilitiesKHR()
        capabilities = vkGetPhysicalDeviceSurfaceCapabilitiesKHR(self.physical_device, self.surface, capabilities)
        self.swapchain_extent = capabilities.currentExtent
        format_count = c_uint32(0)
        formats = vkGetPhysicalDeviceSurfaceFormatsKHR(self.physical_device, self.surface)
        if not formats:
            raise RuntimeError("No surface formats available")
        format = next((f.format for f in formats if
                       f.format == vk.VK_FORMAT_B8G8R8A8_UNORM and f.colorSpace == vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR),
                      formats[0].format)
        swapchain_create_info = vk.VkSwapchainCreateInfoKHR(
            surface=self.surface,
            minImageCount=capabilities.minImageCount + 1,
            imageFormat=format,
            imageColorSpace=vk.VK_COLOR_SPACE_SRGB_NONLINEAR_KHR,
            imageExtent=capabilities.currentExtent,
            imageArrayLayers=1,
            imageUsage=vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT,
            preTransform=capabilities.currentTransform,
            compositeAlpha=vk.VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
            presentMode=vk.VK_PRESENT_MODE_FIFO_KHR,
            clipped=True
        )
        self.swapchain = vkCreateSwapchainKHR(self.device, swapchain_create_info, None, None)
        self.swapchain_images = vkGetSwapchainImagesKHR(self.device, self.swapchain)
        self.swapchain_image_views = []
        for image in self.swapchain_images:
            image_view_create_info = vk.VkImageViewCreateInfo(
                image=image,
                viewType=vk.VK_IMAGE_VIEW_TYPE_2D,
                format=format,
                components=vk.VkComponentMapping(r=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 g=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 b=vk.VK_COMPONENT_SWIZZLE_IDENTITY,
                                                 a=vk.VK_COMPONENT_SWIZZLE_IDENTITY),
                subresourceRange=vk.VkImageSubresourceRange(aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT,
                                                            baseMipLevel=0, levelCount=1,
                                                            baseArrayLayer=0, layerCount=1)
            )
            self.swapchain_image_views.append(vk.vkCreateImageView(self.device, image_view_create_info, None))
        # Recreate framebuffers
        self.framebuffers = []
        for image_view in self.swapchain_image_views:
            framebuffer_create_info = vk.VkFramebufferCreateInfo(
                renderPass=self.render_pass,
                attachmentCount=1,
                pAttachments=[image_view],
                width=self.swapchain_extent.width,
                height=self.swapchain_extent.height,
                layers=1
            )
            self.framebuffers.append(vk.vkCreateFramebuffer(self.device, framebuffer_create_info, None))
        # Recreate command buffers
        vk.vkDestroyCommandPool(self.device, self.command_pool, None)
        command_pool_create_info = vk.VkCommandPoolCreateInfo(
            queueFamilyIndex=self.queue_family_index,
            flags=vk.VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT
        )
        self.command_pool = vk.vkCreateCommandPool(self.device, command_pool_create_info, None)
        command_buffer_allocate_info = vk.VkCommandBufferAllocateInfo(
            commandPool=self.command_pool,
            level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
            commandBufferCount=len(self.swapchain_images)
        )
        self.command_buffers = vk.vkAllocateCommandBuffers(self.device, command_buffer_allocate_info)
        self.needs_resize = False

    def create_render_pass(self):
        color_attachment = vk.VkAttachmentDescription(
            format=vk.VK_FORMAT_B8G8R8A8_UNORM,
            samples=vk.VK_SAMPLE_COUNT_1_BIT,
            loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
            stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=vk.VK_IMAGE_LAYOUT_PRESENT_SRC_KHR
        )
        color_attachment_ref = vk.VkAttachmentReference(
            attachment=0,
            layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL
        )
        subpass = vk.VkSubpassDescription(
            pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            colorAttachmentCount=1,
            pColorAttachments=[color_attachment_ref]
        )
        render_pass_create_info = vk.VkRenderPassCreateInfo(
            attachmentCount=1,
            pAttachments=[color_attachment],
            subpassCount=1,
            pSubpasses=[subpass]
        )
        return vk.vkCreateRenderPass(self.device, render_pass_create_info, None)

    def create_framebuffers(self):
        framebuffers = []
        for image_view in self.swapchain_image_views:
            framebuffer_create_info = vk.VkFramebufferCreateInfo(
                renderPass=self.render_pass,
                attachmentCount=1,
                pAttachments=[image_view],
                width=self.swapchain_extent.width,
                height=self.swapchain_extent.height,
                layers=1
            )
            framebuffers.append(vk.vkCreateFramebuffer(self.device, framebuffer_create_info, None))
        return framebuffers

    def create_pipeline(self):
        vertex_shader = get_shader(os.path.join(dir_path, "vk_quad.vert"))
        fragment_shader = get_shader(os.path.join(dir_path, "vk_pyr_quads.frag"))
        vert_module = vk.vkCreateShaderModule(self.device, vk.VkShaderModuleCreateInfo(codeSize=len(vertex_shader),
                                                                                       pCode=vertex_shader), None)
        frag_module = vk.vkCreateShaderModule(self.device, vk.VkShaderModuleCreateInfo(codeSize=len(fragment_shader),
                                                                                       pCode=fragment_shader), None)
        shader_stages = [
            vk.VkPipelineShaderStageCreateInfo(
                stage=vk.VK_SHADER_STAGE_VERTEX_BIT,
                module=vert_module,
                pName="main"
            ),
            vk.VkPipelineShaderStageCreateInfo(
                stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
                module=frag_module,
                pName="main"
            )
        ]
        vertex_input_info = vk.VkPipelineVertexInputStateCreateInfo()
        input_assembly = vk.VkPipelineInputAssemblyStateCreateInfo(
            topology=vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
            primitiveRestartEnable=False
        )
        viewport = vk.VkViewport(
            x=0, y=0,
            width=float(self.swapchain_extent.width),
            height=float(self.swapchain_extent.height),
            minDepth=0.0, maxDepth=1.0
        )
        scissor = vk.VkRect2D(offset=vk.VkOffset2D(x=0, y=0),
                              extent=self.swapchain_extent)
        viewport_state = vk.VkPipelineViewportStateCreateInfo(
            viewportCount=1,
            pViewports=[viewport],
            scissorCount=1,
            pScissors=[scissor]
        )
        rasterizer = vk.VkPipelineRasterizationStateCreateInfo(
            depthClampEnable=False,
            rasterizerDiscardEnable=False,
            polygonMode=vk.VK_POLYGON_MODE_FILL,
            cullMode=vk.VK_CULL_MODE_NONE,
            frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE,
            lineWidth=1.0
        )
        multisampling = vk.VkPipelineMultisampleStateCreateInfo(
            rasterizationSamples=vk.VK_SAMPLE_COUNT_1_BIT
        )
        color_blend_attachment = vk.VkPipelineColorBlendAttachmentState(
            blendEnable=False,
            colorWriteMask=vk.VK_COLOR_COMPONENT_R_BIT | vk.VK_COLOR_COMPONENT_G_BIT |
                           vk.VK_COLOR_COMPONENT_B_BIT | vk.VK_COLOR_COMPONENT_A_BIT
        )
        color_blending = vk.VkPipelineColorBlendStateCreateInfo(
            logicOpEnable=False,
            attachmentCount=1,
            pAttachments=[color_blend_attachment]
        )
        self.descriptor_set_layout = vk.vkCreateDescriptorSetLayout(
            self.device,
            vk.VkDescriptorSetLayoutCreateInfo(
                bindingCount=7,
                pBindings=[
                    vk.VkDescriptorSetLayoutBinding(binding=0, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=1, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=2, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=3, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=4, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=5, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                    vk.VkDescriptorSetLayoutBinding(binding=6, descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=1, stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT),
                ]
            ),
            None
        )
        pipeline_layout = vk.vkCreatePipelineLayout(
            self.device,
            vk.VkPipelineLayoutCreateInfo(
                setLayoutCount=1,
                pSetLayouts=[self.descriptor_set_layout]
            ),
            None
        )
        dynamic_states = [vk.VK_DYNAMIC_STATE_VIEWPORT, vk.VK_DYNAMIC_STATE_SCISSOR]
        dynamic_state_info = vk.VkPipelineDynamicStateCreateInfo(
            sType=vk.VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
            dynamicStateCount=len(dynamic_states),
            pDynamicStates=dynamic_states
        )
        pipeline_create_info = vk.VkGraphicsPipelineCreateInfo(
            stageCount=2,
            pStages=shader_stages,
            pVertexInputState=vertex_input_info,
            pInputAssemblyState=input_assembly,
            pViewportState=viewport_state,
            pRasterizationState=rasterizer,
            pMultisampleState=multisampling,
            pColorBlendState=color_blending,
            pDynamicState=dynamic_state_info,
            pDepthStencilState=None,
            layout=pipeline_layout,
            renderPass=self.render_pass,
            subpass=0
        )
        pipeline = vk.vkCreateGraphicsPipelines(self.device, None, 1, [pipeline_create_info], None)[0]
        return pipeline, pipeline_layout, [vert_module, frag_module]

    def create_buffers(self):
        buffers = {}
        buffer_sizes = {
            'input_texture': 4 * 1920 * 1080 * 4 * 3,
            'input_texture_infos': 4 * 30 * 9 * 4 + 4 * 2,
            'user_input': len(UserInputUBO().to_bytes()),
            'user_output': len(UserOutputUBO().to_bytes()),
            'input_name': 16384,
            'input_name_ptr': 1024
        }
        for name, size in buffer_sizes.items():
            buffer_create_info = vk.VkBufferCreateInfo(
                size=size,
                usage=vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
                sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
            )
            buffer = vk.vkCreateBuffer(self.device, buffer_create_info, None)
            memory_requirements = vk.vkGetBufferMemoryRequirements(self.device, buffer)
            memory_type_index = next(i for i, mt in enumerate(vk.vkGetPhysicalDeviceMemoryProperties(self.physical_device).memoryTypes)
                                     if mt.propertyFlags & vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
            memory_allocate_info = vk.VkMemoryAllocateInfo(
                allocationSize=memory_requirements.size,
                memoryTypeIndex=memory_type_index
            )
            memory = vk.vkAllocateMemory(self.device, memory_allocate_info, None)
            vk.vkBindBufferMemory(self.device, buffer, memory, 0)
            buffers[name] = {'buffer': buffer, 'memory': memory}
        return buffers

    def create_descriptor_sets(self):
        pool_sizes = [
            vk.VkDescriptorPoolSize(type=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, descriptorCount=7)
        ]
        descriptor_pool_create_info = vk.VkDescriptorPoolCreateInfo(
            maxSets=1,
            poolSizeCount=len(pool_sizes),
            pPoolSizes=pool_sizes
        )
        descriptor_pool = vk.vkCreateDescriptorPool(self.device, descriptor_pool_create_info, None)
        descriptor_set_allocate_info = vk.VkDescriptorSetAllocateInfo(
            descriptorPool=descriptor_pool,
            descriptorSetCount=1,
            pSetLayouts=[self.descriptor_set_layout]
        )
        descriptor_sets = vk.vkAllocateDescriptorSets(self.device, descriptor_set_allocate_info)
        WHOLE_SIZE = 0xFFFFFFFFFFFFFFFF # Equivalent to VK_WHOLE_SIZE (-1 as unsigned), bypassing cffi blocking that
        descriptor_writes = [
            vk.VkDescriptorBufferInfo(buffer=self.buffers['input_texture']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['input_texture_infos']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['user_input']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['user_output']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['font_image']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['glyph_buffer']['buffer'], offset=0, range=WHOLE_SIZE),
            vk.VkDescriptorBufferInfo(buffer=self.buffers['input_name']['buffer'], offset=0, range=WHOLE_SIZE),
        ]
        write_descriptor_sets = [
            vk.VkWriteDescriptorSet(
                dstSet=descriptor_sets[0],
                dstBinding=i,
                descriptorCount=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                pBufferInfo=[descriptor_writes[i]]
            ) for i in range(7)
        ]
        vk.vkUpdateDescriptorSets(self.device, len(write_descriptor_sets), write_descriptor_sets, 0, None)
        return descriptor_pool, descriptor_sets

    def load_font_atlas(self, npz_data):
        atlas_texture = npz_data['atlas_texture']
        atlas_metadata = npz_data['metadata'].item()
        # Font image buffer
        atlas_data_bytes = bytearray()
        atlas_data_bytes.extend(struct.pack("<2i", *atlas_texture.shape))
        atlas_data_bytes.extend(atlas_texture.tobytes())
        buffer_create_info = vk.VkBufferCreateInfo(
            size=len(atlas_data_bytes),
            usage=vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        font_image_buffer = vk.vkCreateBuffer(self.device, buffer_create_info, None)
        memory_requirements = vk.vkGetBufferMemoryRequirements(self.device, font_image_buffer)
        memory_type_index = next(i for i, mt in enumerate(vk.vkGetPhysicalDeviceMemoryProperties(self.physical_device).memoryTypes)
                                 if mt.propertyFlags & vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT)
        memory_allocate_info = vk.VkMemoryAllocateInfo(
            allocationSize=memory_requirements.size,
            memoryTypeIndex=memory_type_index
        )
        font_image_memory = vk.vkAllocateMemory(self.device, memory_allocate_info, None)
        vk.vkBindBufferMemory(self.device, font_image_buffer, font_image_memory, 0)
        atlas_data_bytes = vk.vkMapMemory(self.device, font_image_memory, 0, len(atlas_data_bytes), 0)
        vk.vkUnmapMemory(self.device, font_image_memory)
        self.buffers['font_image'] = {'buffer': font_image_buffer, 'memory': font_image_memory}
        # Glyph buffer
        glyph_data_bytes = bytearray()
        glyph_data_bytes.extend(struct.pack("<1i", len(atlas_metadata)))
        for c, bbox in atlas_metadata.items():
            glyph_data_bytes.extend(struct.pack("<5i", ord(c), bbox[1], bbox[0], bbox[3], bbox[2]))
        buffer_create_info = vk.VkBufferCreateInfo(
            size=len(glyph_data_bytes),
            usage=vk.VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE
        )
        glyph_buffer = vk.vkCreateBuffer(self.device, buffer_create_info, None)
        memory_requirements = vk.vkGetBufferMemoryRequirements(self.device, glyph_buffer)
        memory_allocate_info = vk.VkMemoryAllocateInfo(
            allocationSize=memory_requirements.size,
            memoryTypeIndex=memory_type_index
        )
        glyph_memory = vk.vkAllocateMemory(self.device, memory_allocate_info, None)
        vk.vkBindBufferMemory(self.device, glyph_buffer, glyph_memory, 0)
        glyph_data_bytes = vk.vkMapMemory(self.device, glyph_memory, 0, len(glyph_data_bytes), 0)
        vk.vkUnmapMemory(self.device, glyph_memory)
        self.buffers['glyph_buffer'] = {'buffer': glyph_buffer, 'memory': glyph_memory}

    def update_buffers(self):
        # Update input texture buffer
        self.input_texture_infos_ubo.get_input_image_buffer(
            self.write_buffer,
            self.device, self.queue, self.buffers['input_texture']['buffer']
        )
        # Update texture infos buffer
        tex_data = self.input_texture_infos_ubo.get_tex_data_buffer()
        self.write_buffer(tex_data, 0, self.buffers['input_texture_infos']['buffer'], self.device, self.queue)
        # Update name buffers
        names, name_ptrs = self.input_texture_infos_ubo.get_name_str_buffers()
        self.write_buffer(names, 0, self.buffers['input_name']['buffer'], self.device, self.queue)
        self.write_buffer(name_ptrs, 0, self.buffers['input_name_ptr']['buffer'], self.device, self.queue)
        # Update user input buffer
        self.write_buffer(self.user_input_ubo.to_bytes(), 0, self.buffers['user_input']['buffer'], self.device, self.queue)
        # Read user output buffer
        data_ptr = vk.vkMapMemory(self.device, self.buffers['user_output']['memory'], 0, len(self.user_output_ubo.to_bytes()), 0)
        #out_data = vk.memcpy(data_ptr, len(self.user_output_ubo.to_bytes()))
        # ADDED: Invalidate non-coherent memory so CPU sees GPU-written data
        flush_range = vk.VkMappedMemoryRange(
            memory=self.buffers['user_output']['memory'], offset=0,
            size=len(self.user_output_ubo.to_bytes())
        )
        vk.vkInvalidateMappedMemoryRanges(self.device, 1, [flush_range])
        # Read the mapped memory into Python
        #buf = ffi.buffer(data_ptr, len(self.user_output_ubo.to_bytes()))
        buf = bytes(data_ptr)
        self.user_output_ubo.hit_level = struct.unpack("<i", buf[0:4])[0]
        self.user_output_ubo.hit_pos = struct.unpack("<ff", buf[8:])[0]

        vk.vkUnmapMemory(self.device, self.buffers['user_output']['memory'])
        self.user_output_ubo.hit_level = struct.unpack("<i", data_ptr[0:4])[0]
        self.user_output_ubo.hit_pos = struct.unpack("<ff", data_ptr[8:])

    def write_buffer(self, data, offset, buffer, device, queue):
        memory = self.buffers[[k for k, v in self.buffers.items() if v['buffer'] == buffer][0]]['memory']
        data_ptr = vk.vkMapMemory(device, memory, offset, len(data), 0)
        #data_ptr[:] = data
        ffi.memmove(data_ptr, data, len(data))  # UPDATED: Use memmove to get LLMs to shut the fuck up
        flush_range = vk.VkMappedMemoryRange(memory=memory, offset=offset, size=len(data))
        vk.vkFlushMappedMemoryRanges(device, 1, [flush_range])
        vk.vkUnmapMemory(device, memory)

    def update(self):
        while True:
            if self.needs_resize or not self.swapchain:
                self.recreate_swapchain()
                if not self.swapchain:  # Window minimized
                    return
            try:
                vk.vkWaitForFences(self.device, 1, [self.fence], True, 2**64 - 1)
                vk.vkResetFences(self.device, 1, [self.fence])
                image_index = vkAcquireNextImageKHR(self.device, self.swapchain, 2**64 - 1,
                                                       self.semaphore_image_available, None)
                vk.vkResetCommandBuffer(self.command_buffers[image_index], 0)
                command_buffer = self.command_buffers[image_index]
                begin_info = vk.VkCommandBufferBeginInfo()
                vk.vkBeginCommandBuffer(command_buffer, begin_info)
                render_pass_info = vk.VkRenderPassBeginInfo(
                    renderPass=self.render_pass,
                    framebuffer=self.framebuffers[image_index],
                    renderArea=vk.VkRect2D(offset=vk.VkOffset2D(x=0, y=0),
                                           extent=vk.VkExtent2D(width=glfw.get_window_size(self.window)[0],
                                                                height=glfw.get_window_size(self.window)[1])),
                    clearValueCount=1,
                    pClearValues=[vk.VkClearValue(color=vk.VkClearColorValue(float32=[1.0, 1.0, 1.0, 1.0]))]
                )
                vk.vkCmdBeginRenderPass(command_buffer, render_pass_info, vk.VK_SUBPASS_CONTENTS_INLINE)
                vk.vkCmdBindPipeline(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.pipeline)
                vk.vkCmdBindDescriptorSets(command_buffer, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                                           self.pipeline_layout, 0, 1, self.descriptor_sets, 0, None)
                width, height = glfw.get_window_size(self.window)
                viewport = vk.VkViewport(x=0, y=0, width=float(width), height=float(height),
                                         minDepth=0.0, maxDepth=1.0)
                scissor = vk.VkRect2D(offset=vk.VkOffset2D(x=0, y=0),
                                      extent=vk.VkExtent2D(width=width, height=height))
                vk.vkCmdSetViewport(command_buffer, 0, 1, [viewport])
                vk.vkCmdSetScissor(command_buffer, 0, 1, [scissor])
                vk.vkCmdDraw(command_buffer, 6, 1, 0, 0)  # Full-screen quad
                vk.vkCmdEndRenderPass(command_buffer)
                vk.vkEndCommandBuffer(command_buffer)
                submit_info = vk.VkSubmitInfo(
                    waitSemaphoreCount=1,
                    pWaitSemaphores=[self.semaphore_image_available],
                    pWaitDstStageMask=[vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT],
                    commandBufferCount=1,
                    pCommandBuffers=[command_buffer],
                    signalSemaphoreCount=1,
                    pSignalSemaphores=[self.semaphore_render_finished]
                )
                vk.vkQueueSubmit(self.queue, 1, [submit_info], self.fence)
                present_info = vk.VkPresentInfoKHR(
                    waitSemaphoreCount=1,
                    pWaitSemaphores=[self.semaphore_render_finished],
                    swapchainCount=1,
                    pSwapchains=[self.swapchain],
                    pImageIndices=[image_index]
                )
                vkQueuePresentKHR(self.queue, present_info)
                break
            except vk.VkErrorOutOfDateKhr:
                self.recreate_swapchain()
                continue



    def cleanup(self):
        print("cleanup entered")
        vk.vkDeviceWaitIdle(self.device)
        vk.vkDestroySemaphore(self.device, self.semaphore_image_available,None)
        vk.vkDestroySemaphore(self.device, self.semaphore_render_finished,None)
        vk.vkDestroyFence(self.device, self.fence, None)
        for module in self.shader_modules:
            vk.vkDestroyShaderModule(self.device, module, None)
        for name, buf in self.buffers.items():
            vk.vkDestroyBuffer(self.device, buf['buffer'], None)
            vk.vkFreeMemory(self.device, buf['memory'], None)
        vk.vkDestroyDescriptorPool(self.device, self.descriptor_pool, None)
        vk.vkDestroyPipeline(self.device, self.pipeline, None)
        vk.vkDestroyPipelineLayout(self.device, self.pipeline_layout, None)
        vk.vkDestroyDescriptorSetLayout(self.device, self.descriptor_set_layout,None)
        for framebuffer in self.framebuffers:
            vk.vkDestroyFramebuffer(self.device, framebuffer, None)
        vk.vkDestroyRenderPass(self.device, self.render_pass, None)
        for image_view in self.swapchain_image_views:
            vk.vkDestroyImageView(self.device, image_view, None)
        vkDestroySwapchainKHR(self.device, self.swapchain, None)
        vkDestroySurfaceKHR(self.instance, self.surface, None)
        vk.vkDestroyCommandPool(self.device, self.command_pool, None)
        vk.vkDestroyDevice(self.device, None)
        vk.vkDestroyInstance(self.instance, None)
        print("cleanup finished")

class VulkanWindow:
    def __init__(self, title="Vulkan Window", size=(1280, 720), vsync=True):
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")
        glfw.window_hint(glfw.CLIENT_API, glfw.NO_API)
        glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
        self.window = glfw.create_window(size[0], size[1], title, None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")
        glfw.set_window_user_pointer(self.window, self)
        self.app = VulkanApp(self.window)
        self.window_names = {}
        self.csr_window_names = {}
        self.timer = glfw.get_time()

        # Set callbacks
        glfw.set_window_close_callback(self.window, self.window_close_callback)
        glfw.set_cursor_pos_callback(self.window, self.mouse_position_callback)
        glfw.set_scroll_callback(self.window, self.mouse_scroll_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_key_callback(self.window, self.key_callback)

    def window_close_callback(self, window):
        print("Window close requested")
        glfw.set_window_should_close(window, glfw.TRUE)

    def mouse_position_callback(self, window, x, y):
        if self.app.user_input_ubo is not None:
            self.app.user_input_ubo.iMouse[0] = float(x)
            self.app.user_input_ubo.iMouse[1] = float(y)
        if self.app.user_output_ubo is not None:
            frame = self.app.user_output_ubo.hit_level
            if frame != -1:
                self.app.last_frame = frame
                self.app.user_input_ubo.sel_lvl[0] = frame

    def mouse_scroll_callback(self, window, x_offset, y_offset):
        if self.app.user_output_ubo is not None and self.app.last_frame != -1:
            rect = self.app.input_texture_infos_ubo.tex_levels[self.app.last_frame]['rect']
            swap = self.app.input_texture_infos_ubo.tex_levels[self.app.last_frame]['flags'] & 8
            width = self.app.input_texture_infos_ubo.tex_levels[self.app.last_frame]['width']
            height = self.app.input_texture_infos_ubo.tex_levels[self.app.last_frame]['height']
            scale_factor = 0.1 * y_offset
            width_adjustment = width * scale_factor
            height_adjustment = height * scale_factor
            rect[0] -= width_adjustment / 2
            rect[1] -= height_adjustment / 2
            rect[2] += width_adjustment / 2
            rect[3] += height_adjustment / 2

    def mouse_button_callback(self, window, button, action, mods):
        if action == glfw.PRESS:
            x, y = glfw.get_cursor_pos(window)
            if self.app.user_input_ubo is not None:
                self.app.user_input_ubo.iMouse[0] = float(x)
                self.app.user_input_ubo.iMouse[1] = float(y)
            if self.app.user_output_ubo is not None:
                frame = self.app.user_output_ubo.hit_level
                if frame != -1:
                    self.app.last_frame = frame
                    self.app.user_input_ubo.sel_lvl[0] = frame

    def key_callback(self, window, key, scancode, action, mods):
        if key == glfw.KEY_P and action == glfw.PRESS:
            rects = [(r['rect'][2] - r['rect'][0], r['rect'][3] - r['rect'][1])
                     for r in self.app.input_texture_infos_ubo.tex_levels]
            packer = newPacker(
                mode=PackingMode.Offline,
                pack_algo=MaxRectsBaf,
                bin_algo=PackingBin.BFF,
                sort_algo=SORT_AREA,
                rotation=False
            )
            bins = [(glfw.get_window_size(self.window)[1], glfw.get_window_size(self.window)[0])]
            for i, r in enumerate(rects):
                packer.add_rect(*r, rid=i)
            for b in bins:
                packer.add_bin(*b)
            packer.pack()
            for rect in packer.rect_list():
                _, x, y, w, h, rid = rect
                self.app.input_texture_infos_ubo.tex_levels[rid]['rect'] = [x, y, x + w, y + h]

    def imshow(self, window_name, frame):
        if frame.dtype in [np.float32, np.float64]:
            frame = (frame * 255).astype(np.uint8)
        elif frame.dtype not in [np.uint8, np.int8]:
            frame = frame.astype(np.uint8)
        if (scipy_available and isinstance(frame, scipy.sparse.csr_matrix)) or \
           (pytorch_available and isinstance(frame, torch.Tensor) and frame.layout == torch.sparse_csr):
            if window_name in self.csr_window_names:
                i = self.csr_window_names[window_name]
                self.app.input_texture_infos_ubo.set_csr_input_stream(i, frame, name=window_name, flags=9)
            else:
                self.csr_window_names[window_name] = self.app.input_texture_infos_ubo.append_csr_input_stream(frame, name=window_name, flags=9)
        else:
            if window_name in self.window_names:
                i = self.window_names[window_name]
                self.app.input_texture_infos_ubo.set_input_stream(i, frame, name=window_name, flags=9)
            else:
                self.window_names[window_name] = self.app.input_texture_infos_ubo.append_input_stream(frame, name=window_name, flags=9)

    def update(self):
        if glfw.window_should_close(self.window):
            self.app.cleanup()
            glfw.terminate()
            return False
        self.app.update_buffers()
        self.app.update()
        glfw.poll_events()
        return True
