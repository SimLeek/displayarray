#version 450

layout(location = 0) out vec2 out_position;

void main() {
    vec2 positions[6] = vec2[](
        vec2(-1.0, -1.0),
        vec2(1.0, -1.0),
        vec2(1.0, 1.0),
        vec2(-1.0, -1.0),
        vec2(1.0, 1.0),
        vec2(-1.0, 1.0)
    );
    out_position = positions[gl_VertexIndex];
    gl_Position = vec4(out_position, 0.0, 1.0);
}
