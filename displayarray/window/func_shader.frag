#version 430

struct ViewportSettings {
    vec2 min_xy;
    vec2 max_xy;
};

uniform ViewportSettings viewport;

struct QuadNode {
    int children[4];
    int line_start;
    int line_count;
    int text_start;
    int text_count;
};

struct TextItem {
    vec2 position;
    int string_start;
    int string_length;
};

struct Glyph {
    int char_ord;
    int x_offset;
    int y_offset;
    int width;
    int height;
};

layout(std430, binding=0) buffer QuadTree {
    QuadNode nodes[];
};

layout(std430, binding=1) buffer LineIndices {
    int line_indices[];
};

layout(std430, binding=2) buffer TextIndices {
    int text_indices[];
};

layout(std430, binding=3) buffer LinePositions {
    vec4 positions[];
};

layout(std430, binding=4) buffer LineColors {
    vec4 colors[];
};

layout(std430, binding=5) buffer LineWidths {
    float widths[];
};

layout(std430, binding=6) buffer TextItems {
    TextItem text_items[];
};

layout(std430, binding=7) buffer Strings {
    int strings[];
};

layout(std430, binding=8) buffer Glyphs {
    Glyph glyphs[];
};

uniform sampler2D font_texture;
uniform vec2 window_size;
uniform float anti_aliasing_factor;
uniform float font_scale;
uniform int num_glyphs;
uniform int font_image_width;
uniform int font_image_height;

layout(origin_upper_left, pixel_center_integer) in vec4 gl_FragCoord;
layout(location=0) out vec4 out_color;

int binary_search_glyph(int char_code) {
    int low = 0;
    int high = num_glyphs - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        if (glyphs[mid].char_ord < char_code) {
            low = mid + 1;
        } else if (glyphs[mid].char_ord > char_code) {
            high = mid - 1;
        } else {
            return mid;
        }
    }
    return -1;
}

Glyph get_glyph(int char_code) {
    int index = binary_search_glyph(char_code);
    if (index != -1) {
        return glyphs[index];
    } else {
        int replacement_char = 0xFFFD; // Unicode replacement character
        index = binary_search_glyph(replacement_char);
        if (index != -1) {
            return glyphs[index];
        } else {
            return Glyph(-1, 0, 0, 0, 0);
        }
    }
}

float line_segment_distance(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a;
    vec2 ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h);
}

float y_size = viewport.max_xy.y - viewport.min_xy.y;

vec4 blendCurve(vec4 backgroundColor, vec4 curveColor, float delta)
{
    delta *= 0.7*1000;
    float alpha = exp2(-delta*delta);
    return mix(backgroundColor, curveColor, alpha);
}

void main() {
    // Initialize color with background
    vec4 color = vec4(0.9, 0.9, 0.9, 1.0); // Light gray background

    // Compute viewport dimensions
    vec2 viewport_size = viewport.max_xy - viewport.min_xy;

    // Determine grid spacing (1 to 10 big grid lines in viewport)
    float big_grid_spacing = pow(10.0, ceil(log(viewport_size.x/20)/log(10.0)));
    float small_grid_spacing = big_grid_spacing / 10.0;

    // Map pixel coordinates to viewport space
    vec2 uv = (gl_FragCoord.xy/window_size) * viewport_size + viewport.min_xy;
    vec2 uv_normalized = (uv - viewport.min_xy) / viewport_size;
    //vec2 un_uv = (uv)/viewport_size * window_size;

    // Grid calculation (inspired by your minimal code)
    vec2 small_grid = (abs(0.5- fract(uv / small_grid_spacing - 0.5)) * 0.4)/8;
    vec2 big_grid = (abs(0.5 - fract(uv / big_grid_spacing - 0.5)) * 2.0)/8;

    // Blend grid lines
    //color = mix(color, vec4(vec3(0.8), 1.0), min(small_grid.x, small_grid.y)); // Light gray small grid
    //color = mix(color, vec4(vec3(0.0), 1.0), min(big_grid.x, big_grid.y));    // Black big grid
    color = blendCurve(color, vec4(0.8, 0.8, 0.8, 1.0), min(small_grid.x, small_grid.y));
    color = blendCurve(color, vec4(0.0, 0.0, 0.0, 1.0), min(big_grid.x, big_grid.y));

    // Traverse quadtree
    int node = 0;
    vec2 min_bound = viewport.min_xy;
    vec2 max_bound = viewport.max_xy;
    while (true) {
        QuadNode n = nodes[node];
        if (n.children[0] == -1 && n.children[1] == -1 &&
            n.children[2] == -1 && n.children[3] == -1) {
            break;
        }
        vec2 mid = (min_bound + max_bound) / 2.0;
        int child_index;
        if (uv.x < mid.x) {
            if (uv.y < mid.y) {
                child_index = 0;
                max_bound = mid;
            } else {
                child_index = 2;
                min_bound.y = mid.y;
                max_bound.x = mid.x;
            }
        } else {
            if (uv.y < mid.y) {
                child_index = 1;
                min_bound.x = mid.x;
                max_bound.y = mid.y;
            } else {
                child_index = 3;
                min_bound = mid;
            }
        }
        node = n.children[child_index];
        if (node == -1) return;
    }

    QuadNode leaf = nodes[node];

    // Render lines using middle buffer
    for (int i = 0; i < leaf.line_count; i++) {
        int idx = line_indices[leaf.line_start + i];
        vec2 start = positions[idx].xy;
        vec2 end = positions[idx].zw;
        vec4 line_color = colors[idx];
        float width = widths[idx];
        float dist = (line_segment_distance(uv, start, end)-width);
        dist = dist>0?dist:0;

        float alpha = 0.5 - 0.5 * tanh(5.0 * (dist - width) / anti_aliasing_factor);
        color = blendCurve(color, line_color, dist);
        //color = mix(color, line_color, clamp(alpha, 0.0, 1.0));
                //color = mix(color, vec4(0.0, 0.0, 0.0, 1.0), 0.5);
    }

    // Render text using middle buffer
    for (int i = 0; i < leaf.text_count; i++) {
        int idx = text_indices[leaf.text_start + i];
        TextItem text = text_items[idx];
        vec2 text_pos = text.position;
        int start = text.string_start;
        int str_len = text.string_length;
        float x_offset = 0.0;
        for (int j = 0; j < str_len; j++) {
            int char_code = strings[start + j];
            Glyph glyph = get_glyph(char_code);
            if (glyph.char_ord == -1) continue;
            vec2 glyph_pos = text_pos + vec2(x_offset, 0.0);
            vec2 glyph_size = vec2(glyph.width, glyph.height) * font_scale * y_size;
            vec2 local_uv = (uv - glyph_pos) / glyph_size;
            if (local_uv.x >= 0.0 && local_uv.x <= 1.0 &&
                local_uv.y >= 0.0 && local_uv.y <= 1.0) {
                vec2 tex_uv = vec2(glyph.x_offset + local_uv.x * glyph.width,
                                 glyph.y_offset + local_uv.y * glyph.height) /
                             vec2(font_image_width, font_image_height);
                float alpha = texture(font_texture, tex_uv).r;
                vec4 text_color = vec4(0.0, 0.0, 0.0, alpha);
                color = mix(color, text_color, alpha);
            }
            x_offset += glyph.width * font_scale* y_size;
        }
    }

    out_color = color;
}