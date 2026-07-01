#version 430
in vec2 in_position;
in vec4 in_texcoord_0;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
