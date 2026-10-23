#!/usr/bin/python3
"""Render native boot UI assets; never redraw or modify original Agujita sprites."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runtime'))
from PIL import Image, ImageDraw
import display

root=Path(__file__).resolve().parents[1]

def text_image(value, size, color):
    font=display.font(size)
    box=font.getbbox(value)
    result=Image.new('RGBA',(box[2]+4,box[3]-box[1]+8))
    ImageDraw.Draw(result).text((2,4-box[1]),value,font=font,fill=color)
    return result

image=Image.new('RGB',(1024,768),display.BG)
draw=ImageDraw.Draw(image)
for index,color in enumerate(display.SPECTRUM):
    draw.rectangle((index*1024//5,0,(index+1)*1024//5,3),fill=color)
draw.text((424,145),'LA AGUJA',font=display.font(48,True),fill=display.WHITE)
draw.text((427,211),'RESCUE DISK',font=display.font(27,True),fill=display.CYAN)
draw.text((427,260),'Una pequeña entrada.',font=display.font(20),fill=display.DIM)
draw.text((427,289),'Grandes posibilidades.',font=display.font(20),fill=display.WHITE)
draw.line((427,324,965,324),fill=display.EDGE,width=1)
draw.text((44,711),'↑ ↓ Elegir     Enter Arrancar     E Editar',font=display.font(17),fill=display.DIM)
draw.text((720,711),'TRANSCENDENCEIA',font=display.font(16),fill=display.CYAN)
# Composite the original, unchanged transparent sprite into the native UI.
with Image.open(root/'branding/mascot/idle.png') as sprite:
    image.paste(sprite,(65,140),sprite)
image.save(root/'branding/grub/background.png')
text_image('LA AGUJA  RESCUE DISK',42,display.WHITE).save(root/'branding/plymouth/wordmark.png')
text_image('Una pequeña entrada. Grandes posibilidades.',21,display.DIM).save(root/'branding/plymouth/tagline.png')
dot=Image.new('RGBA',(8,8))
ImageDraw.Draw(dot).ellipse((1,1,7,7),fill=display.GOLD)
dot.save(root/'branding/plymouth/dot.png')
