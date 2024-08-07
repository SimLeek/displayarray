#version 430

//uniform sampler2D FontTexture;

struct TexLevel {
    int startIdx;
    int width;
    int height;
    int flags;
    int channels;
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

/*vec4 print_char(vec2 p, int c)
{
    if (p.x < .0 || p.x > 1. || p.y < 0. || p.y > 1.) return vec4(0, 0, 0, 1e5);
    return textureGrad(FontTexture, p / 16. + fract(vec2(c, 15 - c / 16) / 16.), dFdx(p / 16.), dFdy(p / 16.));
}*/

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
        if (coord.x >= texLevels[sel_level].rect.x - 1 &&
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

            /*vec2 textPos = vec2(texLevels[sel_level].rect.x + 5, texLevels[sel_level].rect.y + 5);
            if (coord.x >= textPos.x && coord.y >= textPos.y &&
                coord.x < textPos.x + 100 && coord.y < textPos.y + 16) // Text area dimensions
            {
                int window_name_ptr = string_ptrs[sel_level];
                int end_ptr = string_ptrs[sel_level+1];
                int char_index = 0;
                vec2 uv = (coord - textPos);
                float FontSize = 8.;
                vec2 U = uv * 64.0 / FontSize;
                vec4 O = vec4(0.0);

                while (char_index < end_ptr) {
                    int char_code = strings[window_name_ptr+char_index];
                    if (char_code == 0) break; // Null terminator for string
                    U.x -= .5; O += print_char(U, char_code);
                    char_index++;
                }

                out_color = mix(out_color, O.xxxx, step(0.0, O.x)); // Blend text over the existing color
            }*/
        }
    }

    if(distance(iMouse, gl_FragCoord.xy)==0){
        hit_level = our_level;
        //hit_pos = vec2(x_current, y_current);
        hit_pos = iMouse;
    }

}