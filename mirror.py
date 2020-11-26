import ctypes
import os
import random
import sys
import subprocess as sp
import time

import numpy as np

import OpenGL.GL as gl
import OpenGL.GL.shaders as shaders
import OpenGL.GLU as glu
import OpenGL.GLUT as glut
from OpenGL.arrays import vbo

from PIL import Image

import pdb

shader = {
    "vert": """
#version 450
layout(location = 0) in vec4 position;
void main() {
    gl_Position = vec4(position.xyz * 2 - 1, 1);
}
""",
    "frag": """
#version 450
layout(location = 0) uniform vec2 window_size;
layout(location = 1) uniform vec2 image_size;
layout(location = 2) uniform sampler2D image_texture;
out vec4 outputColor;
void main() {
    vec2 uv  = gl_FragCoord.xy / window_size;
    uv.y = 1 - uv.y;
    outputColor = texture(image_texture, uv);
}
""",
}

class ADB():

    def __init__(self):
        pass

    def tap(self, x, y, delay=160):
        sp.call(['adb', 'shell', 'input', 'tap', str(x), str(y)])
        time.sleep(0.001 * delay)

    def screencap(self):
        print("screencapping")
        sp.call(['adb', 'shell', 'screencap', '/sdcard/screen.raw'])

    def pull_image(self):
        sp.call(['adb', 'pull', '/sdcard/screen.raw'])


class Controller:

    SCREENCAP_INTERVAL = 0.5

    def __init__(self, scale):
        self.scale = scale
        self.image_width  = w
        self.image_height = h
        self.w, self.h = w, h

        # shader to draw triangles to framebuffer
        self.shader = shaders.compileProgram(
            shaders.compileShader(shader["vert"], gl.GL_VERTEX_SHADER),
            shaders.compileShader(shader["frag"], gl.GL_FRAGMENT_SHADER)
        )
        gl.glUseProgram(self.shader)
        self.image_id = gl.glGetUniformLocation(self.shader, b'image_texture')
        self.image_size_id = gl.glGetUniformLocation(self.shader, b"image_size")
        self.window_size_id = gl.glGetUniformLocation(self.shader, b"window_size")

        # gl texture to store image
        self.image_texture   = gl.glGenTextures(1)

        self.t0 = time.time() + self.SCREENCAP_INTERVAL
        

    def _get_image_data(self):
        data = open("screen.raw", "rb").read()
        w, h = data[0] + data[1] * 256, data[4] + data[5] * 256
        self.image_width  = w
        self.image_height = h
        return data[12:]

    def step(self):
        if time.time() > self.SCREENCAP_INTERVAL + self.t0:
            adb.pull_image()            
            gl.glBindTexture(gl.GL_TEXTURE_2D, self.image_texture)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.image_width, self.image_height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, self._get_image_data())
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            adb.screencap()

            self.t0 += self.SCREENCAP_INTERVAL

    def draw(self):
        gl.glViewport(0, 0, self.w, self.h)

        
        
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glUseProgram(self.shader)
        
        gl.glActiveTexture(gl.GL_TEXTURE0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.image_texture)
        gl.glUniform2f(self.image_size_id, self.image_width, self.image_height)
        gl.glUniform2f(self.window_size_id, self.w, self.h)
        gl.glUniform1i(self.image_id, 0)

        gl.glBegin(gl.GL_QUADS)
        gl.glVertex4f(0, 0, 0, 1)
        gl.glVertex4f(0, 1, 0, 1)
        gl.glVertex4f(1, 1, 0, 1)
        gl.glVertex4f(1, 0, 0, 1)
        gl.glEnd()

        gl.glUseProgram(0)

        gl.glFlush()

    def click(self, button, state, x, y):
        if state == glut.GLUT_DOWN:
            x = (self.image_width  * x) // glut.glutGet(glut.GLUT_WINDOW_WIDTH)
            y = (self.image_height * y) // glut.glutGet(glut.GLUT_WINDOW_HEIGHT)
            adb.tap(x, y)

    def resize(self, w, h):
        gl.glViewport(0, 0, self.w, self.h)
        self.w = w
        self.h = h

    def quit(self):
        exit()

def idle_cb():
    controller.step()
    glut.glutPostRedisplay()
    
def keyboard_cb(key, x, y):
    if key == b'q':
        controller.quit()

def reshape_cb(w, h):
    gl.glViewport(0, 0, glut.glutGet(glut.GLUT_WINDOW_WIDTH), glut.glutGet(glut.GLUT_WINDOW_HEIGHT))
    controller.resize(w, h)

if __name__ == "__main__":
    w, h = (540, 960)

    try:
        scale = float(sys.argv[1])
        scale = abs(scale)
    except ValueError:
        print("Scale must be float")
        exit()
    except IndexError:
        scale = 1

    adb = ADB()

    # Initialize GLUT library
    glut.glutInit()

    # Setup window
    screen_width = glut.glutGet(glut.GLUT_SCREEN_WIDTH)
    screen_height = glut.glutGet(glut.GLUT_SCREEN_HEIGHT)

    glut.glutInitWindowSize(w, h)
    glut.glutInitWindowPosition(0, 0)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)
    glut.glutCreateWindow(b'android-mirror')

    controller = Controller(scale)

    # Register event callbacks
    glut.glutIdleFunc(idle_cb)
    glut.glutDisplayFunc(controller.draw)
    glut.glutKeyboardFunc(keyboard_cb)
    glut.glutMouseFunc(controller.click)
    glut.glutReshapeFunc(reshape_cb)

    glut.glutMainLoop()
