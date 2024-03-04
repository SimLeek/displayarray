#version 430

struct TexLevel {
    int startIdx;
    int width;
    int height;
    int flags;
    vec4 rect; // 4 float representing position on triangle
};

#define TEX_FLAG_HW 8
#define TEX_FLAG_WH 0
#define TEX_FLAG_RGB 0
#define TEX_FLAG_BGR 1

layout(std430, binding = 0) buffer InputBuffer {
    float inputImage[];
};

layout(std430, binding = 1) buffer TexData {
    int channels;
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

layout(origin_upper_left, pixel_center_integer) in vec4 gl_FragCoord;
layout(location = 0) out vec4 out_color;

float bilinearInterpolation(float x, float y, float bottomLeft, float bottomRight, float topLeft, float topRight) {
    float left = mix(topLeft, bottomLeft, y);
    float right = mix(topRight, bottomRight, y);
    return mix(left, right, x);
}

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

        int topLeftIdx = texLevels[our_level].startIdx + int(floor(x_current) * texLevels[our_level].height * channels + floor(y_current) * channels);
        int topRightIdx = topLeftIdx + texLevels[our_level].height * channels;
        int bottomLeftIdx = topLeftIdx + channels;
        int bottomRightIdx = topRightIdx + channels;

        //leave this for visual debugging
        out_color = vec4(float(y_current) / float(levelHeight), float(x_current) / float(levelWidth), 0.0, 1.0);

        out_color.x = bilinearInterpolation(
            fract(x_current),
            fract(y_current),
            inputImage[bottomLeftIdx],
            inputImage[bottomRightIdx],
            inputImage[topLeftIdx],
            inputImage[topRightIdx]
        );
        if (channels > 1) {
            out_color.y = bilinearInterpolation(
                fract(x_current),
                fract(y_current),
                inputImage[bottomLeftIdx + 1],
                inputImage[bottomRightIdx + 1],
                inputImage[topLeftIdx + 1],
                inputImage[topRightIdx + 1]
            );
        }
        if (channels > 2) {
            out_color.z = bilinearInterpolation(
                fract(x_current),
                fract(y_current),
                inputImage[bottomLeftIdx + 2],
                inputImage[bottomRightIdx + 2],
                inputImage[topLeftIdx + 2],
                inputImage[topRightIdx + 2]
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
        }
    }

    if(distance(iMouse, gl_FragCoord.xy)==0){
        hit_level = our_level;
        //hit_pos = vec2(x_current, y_current);
        hit_pos = iMouse;
    }

}