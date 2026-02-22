#!/usr/bin/env python3
"""Create local Steve placeholder PNG (copyright-safe pixel art)."""
from PIL import Image
w, h = 200, 280
img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
pix = img.load()
skin = (139, 90, 43, 255)
shirt = (64, 64, 255, 255)
pants = (64, 64, 128, 255)
# Scale to 200x280 (full body proportions)
for y in range(40, 80):
    for x in range(80, 120):
        pix[x, y] = skin
for y in range(80, 140):
    for x in range(70, 130):
        pix[x, y] = shirt
for y in range(140, 230):
    for x in range(85, 115):
        pix[x, y] = pants
img.save('steve.png')
print('Created steve.png')
