#version 430

//todo:  sparse csr handling
//not using samplers here. None support grayscale int8 with vec2 lookup? wtf?
//uniform sampler2DArrayShadow FontTexture;

struct TexLevel {
    int startIdx;
    int width;
    int height;
    int flags;
    int channels;
    int r_channel; //padding out 128 bits needed before float vec4, and useful for many channel arrays
    int b_channel;
    int g_channel;
    vec4 rect; // 4 float representing position on triangle
};

#define TEX_FLAG_HW 8
#define TEX_FLAG_WH 0
#define TEX_FLAG_RGB 0
#define TEX_FLAG_BGR 1

layout(std430, binding = 0) buffer InputBuffer {
    int inputImage[];
};

layout(std430, binding = 1) buffer TexData {
    int levels;
    TexLevel texLevels[];
};

layout(std430, binding=2) buffer UserInput {
    int sel_level;
    vec2 iMouse;
};

layout(std430, binding=3) buffer UserOutput {
    int hit_level;
    vec2 hit_pos;
};

#define font_size 24

struct Glyph {
    int char_ord;
    int x_offset;
    int y_offset;
    int width;
    int height;
};

layout(std430, binding = 4) buffer FontImageBuffer {
    int font_image_width;
    int font_image_height;
    int fontImage[];
};

layout(std430, binding = 5) buffer GlyphBuffer {
    int num_glyphs;
    Glyph glyphs[];
};

layout(std430, binding = 6) buffer StringBuffer {
    int strings[];
};

layout(std430, binding = 7) buffer StringPtrBuffer {
    int num_strings;
    int string_ptrs[];// should be len(strings)+1 to include last string end location
};

int binary_glyph_search(int value) {
    int low = 0;
    int high = num_glyphs - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        if (glyphs[mid].char_ord < value) {
            low = mid + 1;
        } else if (glyphs[mid].char_ord > value) {
            high = mid - 1;
        } else {
            return mid;
        }
    }
    return -1; // Character not found
}

ivec4 get_char(int char_ord_val) {
    int index = binary_glyph_search(char_ord_val);
    if (index != -1) {
        Glyph g = glyphs[index];
        return ivec4(g.x_offset, g.y_offset, g.width, g.height);
    } else {
        int replacement_char_ord = int(0xFFFD); // Unicode replacement character U+FFFD
        index = binary_glyph_search(replacement_char_ord);
        if (index != -1) {
            Glyph g = glyphs[index];
            return ivec4(g.x_offset, g.y_offset, g.width, g.height);
        } else {
            return ivec4(-1, -1, -1, -1); // fail
        }
    }
}

#define EXTRACT_UINT8_VALUE(value, index) \
    (((value) >> ((index)<<3)) & 0xFFu)
#define EXTRACT_8_FROM_32_ARRAY(array, index) \
    EXTRACT_UINT8_VALUE(array[index >> 2], index & 3)
#define EXTRACT_FLOAT_FROM_INT8_ARRAY(array, index) \
    float(EXTRACT_8_FROM_32_ARRAY(array, index))/255

layout(origin_upper_left, pixel_center_integer) in vec4 gl_FragCoord;
layout(location = 0) out vec4 out_color;

float bilinearInterpolation(float x, float y, float bottomLeft, float bottomRight, float topLeft, float topRight) {
    float left = mix(topLeft, bottomLeft, y);
    float right = mix(topRight, bottomRight, y);
    return mix(left, right, x);
}

float print_char(vec2 p, ivec4 glyph_bbox)
{
    //y_current = int(levelHeight * (p.y - glyph_bbox.y) / (texLevels[our_level].rect.w - texLevels[our_level].rect.y));
    //x_current = int(levelWidth * (coord.x - texLevels[our_level].rect.x) / (texLevels[our_level].rect.z - texLevels[our_level].rect.x));

    int topLeftIdx = int(floor(p.x+glyph_bbox.x) * font_image_height + floor(p.y+glyph_bbox.y));
    /*int topRightIdx = topLeftIdx + font_image_height;
    int bottomLeftIdx = topLeftIdx+1;
    int bottomRightIdx = topRightIdx+1;

    float out_color = bilinearInterpolation(
        fract(p.x),
        fract(p.y),
        EXTRACT_FLOAT_FROM_INT8_ARRAY(fontImage,bottomLeftIdx),
        EXTRACT_FLOAT_FROM_INT8_ARRAY(fontImage,bottomRightIdx),
        EXTRACT_FLOAT_FROM_INT8_ARRAY(fontImage,topLeftIdx),
        EXTRACT_FLOAT_FROM_INT8_ARRAY(fontImage,topRightIdx)
    );*/
    //return out_color;
    return EXTRACT_FLOAT_FROM_INT8_ARRAY(fontImage,topLeftIdx);
}

vec4 fg_color = vec4(.1,.5,.05,1);

void main() {
    int our_level = -1;
    float y_current = -1;
    float x_current = -1;
    vec2 coord;

    for (int i = 0;i < levels; i++) {
        if (bool(texLevels[i].flags & TEX_FLAG_HW)) {
            coord = gl_FragCoord.yx;
        } else {
            coord = gl_FragCoord.xy;
        }
        if (coord.x >= texLevels[i].rect.x &&
        coord.y >= texLevels[i].rect.y &&
        coord.x < texLevels[i].rect.z &&
        coord.y < texLevels[i].rect.w
        ) {
            our_level = i;
            //don't break. All shader instances should get same execution, and this puts later textures on top.
        }
    }

    if (our_level != -1) {
        if (bool(texLevels[our_level].flags & TEX_FLAG_HW)) {
            coord = gl_FragCoord.yx;
        } else {
            coord = gl_FragCoord.xy;
        }

        int levelWidth = texLevels[our_level].width;
        int levelHeight = texLevels[our_level].height;

        y_current = int(levelHeight * (coord.y - texLevels[our_level].rect.y) / (texLevels[our_level].rect.w - texLevels[our_level].rect.y));
        x_current = int(levelWidth * (coord.x - texLevels[our_level].rect.x) / (texLevels[our_level].rect.z - texLevels[our_level].rect.x));

        int topLeftIdx = texLevels[our_level].startIdx + int(floor(x_current) * texLevels[our_level].height * texLevels[our_level].channels + floor(y_current) * texLevels[our_level].channels);
        int topRightIdx = topLeftIdx + texLevels[our_level].height * texLevels[our_level].channels;
        int bottomLeftIdx = topLeftIdx + texLevels[our_level].channels;
        int bottomRightIdx = topRightIdx + texLevels[our_level].channels;

        //leave this for visual debugging
        out_color = vec4(float(y_current) / float(levelHeight), float(x_current) / float(levelWidth), 0.0, 1.0);

        out_color.x = bilinearInterpolation(
            fract(x_current),
            fract(y_current),
            EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomLeftIdx),
            EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomRightIdx),
            EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topLeftIdx),
            EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topRightIdx)
        );
        if (texLevels[our_level].channels > 1) {
            out_color.y = bilinearInterpolation(
                fract(x_current),
                fract(y_current),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomLeftIdx + 1),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomRightIdx + 1),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topLeftIdx + 1),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topRightIdx + 1)
            );
        }else{
            out_color.xyz = out_color.xxx;
        }
        if (texLevels[our_level].channels > 2) {
            out_color.z = bilinearInterpolation(
                fract(x_current),
                fract(y_current),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomLeftIdx + 2),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,bottomRightIdx + 2),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topLeftIdx + 2),
                EXTRACT_FLOAT_FROM_INT8_ARRAY(inputImage,topRightIdx + 2)
            );
        }
        if (bool(texLevels[our_level].flags & TEX_FLAG_BGR)) {
            float temp_color = out_color.x;
            out_color.x = out_color.z;
            out_color.z = temp_color;
        }
        // currently only supporting 3 channels at most.
    } else {
        // nice white background. ( ∩´ ᐜ `∩)
        out_color = vec4(1.0, 1.0, 1.0, 1.0);
    }

    if (sel_level != -1) {
        if (coord.x >= texLevels[sel_level].rect.x - 20 &&
        coord.y >= texLevels[sel_level].rect.y - 1 &&
        coord.x <= texLevels[sel_level].rect.z &&
        coord.y <= texLevels[sel_level].rect.w
        ) {
            if (coord.x == texLevels[sel_level].rect.x - 1 ||
            coord.y == texLevels[sel_level].rect.y - 1 ||
            coord.x == texLevels[sel_level].rect.z ||
            coord.y == texLevels[sel_level].rect.w
            ) {
                out_color = vec4(0.0, 0.5, 0.0, 1.0); // green selection border, on top of everything
            }

            vec4 textPos = vec4(texLevels[sel_level].rect.x-20, texLevels[sel_level].rect.y, texLevels[sel_level].rect.x-20+font_size*2, texLevels[sel_level].rect.w);
            if (coord.x >= textPos.x && coord.y >= textPos.y &&
                coord.x < textPos.z && coord.y < textPos.w) // Text area dimensions
            {
                int window_name_ptr = string_ptrs[sel_level];
                int end_ptr = string_ptrs[sel_level+1];
                vec2 start_uv = textPos.xy;
                vec2 uv = (coord - start_uv);
                int char_index = window_name_ptr;
                float O = 0.0;
                //float y = 0;

                while (char_index < end_ptr) {
                    //y +=.05;
                    int char_code = strings[char_index];
                    ivec4 glyph_bbox = get_char(char_code);
                    if (uv.x>=0 && uv.y>=0 && uv.x<glyph_bbox.z && uv.y<glyph_bbox.w) {
                        O += print_char(uv, glyph_bbox);
                    }
                    start_uv.y += glyph_bbox.w;
                    uv = (coord - start_uv);
                    char_index++;
                }

                out_color = mix(out_color, fg_color, O); // Blend text over the existing color
                //out_color.x = O;
                //out_color.y = y;
                //out_color.z=0;
            }
        }
    }

    if(distance(iMouse, gl_FragCoord.xy)==0){
        hit_level = our_level;
        //hit_pos = vec2(x_current, y_current);
        hit_pos = iMouse;
    }

}