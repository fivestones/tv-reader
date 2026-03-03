#import sys
#import cv2
import tkinter
from tkinter import *
from PIL import ImageTk, Image
from getImageFromPDF import *
from timeit import default_timer as timer
# importing tkinter for gui
import tkinter as tk
from pynput import keyboard

#handle keypresses in a non-blocking way
def on_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(
            key.char))
    except AttributeError:
        print('special key {0} pressed'.format(
            key))
def on_release(key):
    print('{0} released'.format(
        key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False


#check if we are ready to display an image
def checkForImage(pageNumber):
    if os.path.exists("pageImages/" + str(pageNumber).zfill(zeroPadding) + ".png"):
        return True
    else:
        return False


# Collect events in a non-blocking fashion:
listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

doc=fitz.open("blizzard.pdf")
page_count = doc.page_count
imageLeft = doc[0].get_pixmap(alpha=False)
imageRight = doc[1].get_pixmap(alpha=False)

currentLeftPage = 1 #keep track of what page we are on
numPages = 0
zeroPadding = 0

#start getting images from the pdf file
message = ""
print('Starting to get images from PDF in background thread')
#daemon = Thread(target=makeImages, daemon=True, name='makeImages')
#daemon.start()
doc[0]


# creating window
window = tk.Tk()

# setting attribute
window.attributes('-fullscreen', True)
window.title("TV-Reader")

# #check to see if the first images are ready
# while True:
#     print("checking if file exists")
#     if (os.path.exists('pageImages/00.png') & os.path.exists('pageImages/01.png')):
#         print("Now the files are present")
#         break
#     sleep(0.1)
    
# print("out of the while loop")




#time = [timer()]
#imageLeft = img # Image.open("pageImages/00.png")
#time.append(timer())
#imageRight = Image.open("pageImages/01.png")
#time.append(timer())
print("Opened the images")
#print(time)

readyForKeypresses = True

wWidth = window.winfo_width()
wHeight = window.winfo_height()

# print("Image 00.png height and width: ")
# print(imageLeft.size)



biggerHeight = imageLeft.height if imageLeft.height > imageRight.height else imageRight.height

if (imageLeft.width + imageRight.width) / biggerHeight < wWidth / wHeight:
    zoom = wHeight / biggerHeight
else:
    zoom = wWidth / (imageLeft.width + imageRight.width)
mat = fitz.Matrix(zoom, zoom)
imageLeft = doc[0].get_pixmap(matrix=mat, alpha=False)
imageRight = doc[1].get_pixmap(matrix=mat, alpha=False)

# if ((wWidth/(imageLeft.width + imageRight.width)) * biggerHeight) <= wHeight:
#     imageLeft = imageLeft.resize((imageLeft.width/(imageLeft.width + imageRight.width)*wWidth, wHeight), Image.ANTIALIAS)
#     imageRight = imageRight.resize((imageRight.width/(imageRight.width + imageLeft.width) * wWidth, wHeight), Image.ANTIALIAS)
# else:
#     imageLeft = imageLeft.resize((round(wWidth/2), wHeight), Image.ANTIALIAS)
#     imageRight = imageRight.resize((round(wWidth/2), wHeight), Image.ANTIALIAS)

# testLeft = ImageTk.PhotoImage(imageLeft.tobytes("ppm"))
# testRight = ImageTk.PhotoImage(imageRight.tobytes("ppm"))

testLeft = PhotoImage(data = imageLeft.tobytes("ppm"))
testRight = PhotoImage(data = imageRight.tobytes("ppm"))

labelLeft = tkinter.Label(image=testLeft, borderwidth=0)
labelLeft.image = testLeft
labelRight = tkinter.Label(image=testRight, borderwidth=0)
labelRight.image = testRight

labelLeft.place(x=0, y=0)
labelRight.place(x=imageLeft.width, y=0)

# creating text label to display on window screen
#label = tk.Label(window, text="Hello Tkinter!")
#label.pack()

window.mainloop()