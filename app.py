

from tkinter import *
from PIL import ImageTk, Image
from timeit import default_timer as timer
import tkinter as tk
from tkinter import filedialog
import fitz
import os
from threading import Thread

import smbclient.shutil
import smbclient
import os
import threading
import time

from pathlib import Path

import asyncio
import websockets
import socket



########################

async def receive_socket_msg(websocket):
    async for message in websocket:
        handle_messages(message)
        # await websocket.send(message)

async def websocket_connect():
    async with websockets.serve(receive_socket_msg, "0.0.0.0", 55559):
        print("Client connected")
        await asyncio.Future()  # run forever


def websock_messages(): #listen for any incomming connections and process the messages
    asyncio.run(websocket_connect())
    
    #the below is with sockets but not websockets
    # #at the moment this can use the pg-client.py app, run it, and type in the Right Left s ect messages to move the pages
    # server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # server.bind(("localhost", 55559))
    # server.listen(1)
    # server.setblocking(False)

    
    # client = None
    # text = ""
    # running = True
    # while running:

    #     if client is None:
    #         try:
    #             client, address = server.accept()
    #         except BlockingIOError:
    #             pass
    #     else:
    #         try:
    #             raw = client.recv(1024)
    #         except BlockingIOError:
    #             pass
    #         else:
    #             text = raw.decode("utf-8")


    #     if not text == None:
    #         print(text)
    #         handle_messages(text)
    #     text = None

#######################


def handle_messages(message):
    #this function is for both websockets and for keypress events/messages
    global currentLeftPage
    global nextPage
    try:
        print(message)
        if message == "Right":
            currentLeftPage += 2 # turn the page to the right (showing two pages at a time, so go by two)
        elif message == "Left":
            currentLeftPage -= 2 # turn the page to the left
        elif message == "s":
            currentLeftPage +=1 #shift the page to even spreads
        elif message == "b":
            currentLeftPage = -1 # Go to the beginning. Maybe should be 0? This should take into account if the pages were shifted or not
        elif message == "r":
            #get rid of showing the back cover, show only the front cover alone
            pass
        elif message == "1":
            # change to showing only 1 page at a time
            pass
        elif message == "2":
            #change back to showing 2 pages at a time
            pass
        
        if currentLeftPage >= page_count:
            currentLeftPage -= page_count
        if currentLeftPage < 0:
            currentLeftPage += page_count

        nextPage = currentLeftPage + 1
        if nextPage >= page_count:
            nextPage -= page_count
        if nextPage < 0:
            nextPage += page_count
        
        update_images(leftImageNum=currentLeftPage, rightImageNum=nextPage)
    except AttributeError:
        print("there is no keysym key from the key pressed I guess")
    #I don't think we need both a keypress and a keyrelease event
    
    #eventually this will need to respond to network requests instead of just keypresses



def handle_keypress(event):
    try:
        handle_messages(event.keysym)
    except AttributeError:
        print("Error: There is a no keysym key from the key press I guess")

def getProperPageNumber(number, numberToAdd):
    if number + numberToAdd >= page_count:
        return number + numberToAdd - page_count
    elif number + numberToAdd < 0:
        return number + numberToAdd + page_count
    else:
        return number + numberToAdd

def get_next_images(currentLeftPage):
    print("current left page", currentLeftPage)
    # get the next 2 pages
    if image_array[getProperPageNumber(currentLeftPage, 2)] == None or image_array[getProperPageNumber(currentLeftPage, 3)] == None:
        matLeft, matRight, leftZoom = getImagesZoom(doc[getProperPageNumber(currentLeftPage, 2)].rect.width, doc[getProperPageNumber(currentLeftPage, 2)].rect.height, doc[getProperPageNumber(currentLeftPage, 3)].rect.width, doc[getProperPageNumber(currentLeftPage, 3)].rect.height)
        if image_array[getProperPageNumber(currentLeftPage, 2)] == None:
            image_array[getProperPageNumber(currentLeftPage, 2)] = doc[getProperPageNumber(currentLeftPage, 2)].get_pixmap(matrix=matLeft, alpha=False)
        # time.sleep(0.01)
        if image_array[getProperPageNumber(currentLeftPage, 3)] == None:
            image_array[getProperPageNumber(currentLeftPage, 3)] = doc[getProperPageNumber(currentLeftPage, 3)].get_pixmap(matrix=matRight, alpha=False)
        print("got pages {} and {}".format(getProperPageNumber(currentLeftPage, 2), getProperPageNumber(currentLeftPage, 3)))
    
    #get the previous 2 pages
    if image_array[getProperPageNumber(currentLeftPage, -2)] == None or image_array[getProperPageNumber(currentLeftPage, -1)] == None:
        matLeft, matRight, leftZoom = getImagesZoom(doc[getProperPageNumber(currentLeftPage, 2)].rect.width, doc[getProperPageNumber(currentLeftPage, 2)].rect.height, doc[getProperPageNumber(currentLeftPage, 3)].rect.width, doc[getProperPageNumber(currentLeftPage, 3)].rect.height)
        if image_array[getProperPageNumber(currentLeftPage, -2)] == None:
            image_array[getProperPageNumber(currentLeftPage, -2)] = doc[getProperPageNumber(currentLeftPage, -2)].get_pixmap(matrix=matLeft, alpha=False)
        # time.sleep(0.01)
        if image_array[getProperPageNumber(currentLeftPage, -1)] == None:
            image_array[getProperPageNumber(currentLeftPage, -1)] = doc[getProperPageNumber(currentLeftPage, -1)].get_pixmap(matrix=matRight, alpha=False)
        print("got pages {} and {}".format(getProperPageNumber(currentLeftPage, -2), getProperPageNumber(currentLeftPage, -1)))

    


def update_images(leftImageNum, rightImageNum):
    # Set the new imageLeft
    matLeft, matRight, leftZoom = getImagesZoom(doc[leftImageNum].rect.width, doc[leftImageNum].rect.height, doc[rightImageNum].rect.width, doc[rightImageNum].rect.height)

    imageLeft = PhotoImage(data = getImagePixmap(leftImageNum, matLeft).tobytes("ppm"))
    imageRight = PhotoImage(data = getImagePixmap(rightImageNum, matRight).tobytes("ppm"))

    #fix the coordinates of the images containers on the canvas
    print(canvas.coords(leftImage_container))
    print(canvas.coords(rightImage_container))
    canvas.coords(rightImage_container, doc[leftImageNum].rect.width * leftZoom, 0) #set the coords for the left image to be placed right where the left image right edge is

    # set the new imageRight
    canvas.itemconfig(leftImage_container, image=imageLeft)
    canvas.itemconfig(rightImage_container, image=imageRight)
    canvas.nogarbagecollectionLeft = imageLeft
    canvas.nogarbagecollectionRight = imageRight
    canvas.update() #update the canvas because we are goint to fetch the next images next and we don't want to have to wait until that's done to show the updated canvas

    #todo: get the next images ready so they load faster:
    t = threading.Thread(name='get_next_images', target=get_next_images, args=([currentLeftPage]))
    t.start()

    

def getImagePixmap(pdfPageNum, matrix):
    if image_array[pdfPageNum] == None:
        image_array[pdfPageNum] = doc[pdfPageNum].get_pixmap(matrix=matrix, alpha=False)
    return image_array[pdfPageNum]

def getImagesZoom(imageLeftWidth, imageLeftHeight, imageRightWidth, imageRightHeight):
    # Sorts through the image dimensions and figures out the properzoom for each, returns a matrix

    #find which of the two images have the bigger height
    biggerHeight = imageLeftHeight if imageLeftHeight > imageRightHeight else imageRightHeight
    biggerHeightSide = "left" if imageLeftHeight > imageRightHeight else "right"

    #set the zoom to a ration of window height to image height, OR window width to combined image width
    if (imageLeftWidth + imageRightWidth) / biggerHeight < wWidth / wHeight:
        zoom = wHeight / biggerHeight
    else:
        zoom = wWidth / (imageLeftWidth + imageRightWidth)

    #find out if, after zooming the bigger of the two, the other could be zoomed further
    if biggerHeightSide == "left":
        zoomLeft = zoom
        if imageRightWidth / imageRightHeight < (wWidth/2) / wHeight:
            zoomRight = wHeight / imageRightHeight
        else:
            zoomRight = (wWidth/2) / imageRightWidth
    else:
        zoomRight = zoom
        if imageLeftWidth / imageRightHeight < (wWidth/2) / wHeight:
            zoomLeft = wHeight / imageLeftHeight
        else:
            zoomLeft = (wWidth/2) / imageLeftWidth

    matLeft = fitz.Matrix(zoomLeft, zoomLeft)
    matRight = fitz.Matrix(zoomRight, zoomRight)

    return matLeft, matRight, zoomLeft

def copy_progress(source_path, destination_path, file_size):
    """
    Compare 2 files till they're the same and print the progress.

    :type source_path: str
    :param source_path: path to the source file
    :type destination_path: str
    :param destination_path: path to the destination file
    """

    # Making sure the destination path exists
    while not os.path.exists(destination_path):
        print("Waiting\r")
        time.sleep(.01)

    # Keep checking the file size till it's the same as source file
    while file_size != os.path.getsize(destination_path):
        print ("percentage {}".format(int((float(os.path.getsize(destination_path))/float(file_size)) * 100)), end="\r")
        time.sleep(.01)

    print ("percentage 100")


def copy_file(source_path, destination_path):
    """
    Copying a file

    :type source_path: str
    :param source_path: path to the file that needs to be copied
    :type destination_path: str
    :param destination_path: path to where the file is going to be copied
    :rtype: bool
    :return: True if the file copied successfully, False otherwise
    """
    print ("Copying....")
    # shutil.copyfile(source_path, destination_path)
    smbclient.shutil.copy2(source_path, destination_path)

    if os.path.exists(destination_path):
        print ("Done....")
        return True

    print ("Filed...")
    return False

def obtainFile(serverFilePath):
    global doc
    src = serverFilePath
    des = "downloads/" + serverFilePath[29:].replace('\\', '/') #get the part after \\server.local\tv-bookreader\, and change backslashes to forward slashes
    
    #make the folders it needs to go in if they don't exist (these folders match what is on the server to prevent book collisions)
    if not os.path.exists(Path(des).parent):
        Path(des).parent.mkdir(parents=True, exist_ok=True)
    
    #register the smb session so we can connect to the server to get the file
    smbclient.register_session("server.local", username="tv-bookreader", password="password")

    if not os.path.exists(des): #if we don't already have the file
        # Start the copying on a separate thread from the server to local
        t = threading.Thread(name='copying', target=copy_file, args=(src, des))
        t.start()

        copy_progress(src, des, smbclient.stat(src).st_size) #show progress

    #when the file is done being copied, open it with doc=fitz.open(filepath)
    global doc
    doc=fitz.open(des)


doc=""
#filepath = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
filepath = input(r"Enter the remote file path (e.g., \\server.local\tv-bookreader\test.mobi" + "\n")
#src = r"\\server.local\tv-bookreader\test.mobi"
obtainFile(filepath)

page_count = doc.page_count

image_array = [None] * page_count

startingPage = page_count-1 #the idea for this is that this could be used to start us on a different (i.e., not the first) page if we are coming back to this book after having closed it earlier
currentLeftPage = page_count-1 #keep track of what page we are on
nextPage = startingPage + 1 if startingPage + 1 < page_count else startingPage + 1 - page_count




leftPageRect = doc[startingPage]
#rightPageRect = doc[startingPage+1] if startingPage+1 < page_count else doc[startingPage+1-page_count]
rightPageRect = doc[nextPage]
#imageLeft = getImagePixmap[0] #takes the longest
#imageRight = getImagePixmap[1] #takes the longest

# creating window
window = tk.Tk()


# setting attributes
window.overrideredirect(True)
window.overrideredirect(False)
window.attributes('-fullscreen', True) #takes a sec
window.title("TV-Reader")

# Bind keypress event to handle_keypress()
window.bind("<Key>", handle_keypress)

#start listening for a websocket connection and then process any incoming messages
t = threading.Thread(name='websocket', target=websock_messages)
t.start()


############Figure out window and image sizes, and zoom them appropriately for full screen
######This works for two pages, but should also set it to be able to display only one, as some books have a landscape page in the pdf that is meant to be the whole visible page (left and right sides in one image in the pdf). This should be connected to a keypress to change from 2 pages to 1 page visible
wWidth = window.winfo_width()
wHeight = window.winfo_height()

# call the getImagesZoom function here
matLeft, matRight, leftZoom = getImagesZoom(leftPageRect.rect.width, leftPageRect.rect.height, rightPageRect.rect.width, rightPageRect.rect.height)

#put the images in the image_array array so they can quickly be used again later if we go back to those pages
image_array[startingPage] = doc[startingPage].get_pixmap(matrix=matLeft, alpha=False) #split second pause
image_array[nextPage] = doc[nextPage].get_pixmap(matrix=matRight, alpha=False) #split second pause

imageLeft = image_array[startingPage]
imageRight = image_array[nextPage]

testLeft = PhotoImage(data = imageLeft.tobytes("ppm"))
testRight = PhotoImage(data = imageRight.tobytes("ppm"))



########## Make the canvas, add the images to it

canvas = tk.Canvas(window, width=wWidth, height=wHeight, highlightthickness=0) #highlightthickness=0 makes the 2px grey border around the edge of the screen disappear
canvas.pack()

# Add the images to the canvas side by side
leftImage_container = canvas.create_image(0, 0, image=testLeft, anchor=tk.NW)
rightImage_container = canvas.create_image(imageLeft.width, 0, image=testRight, anchor=tk.NW)
canvas.update()

#todo: get the next images ready so they load faster:
t = threading.Thread(name='get_next_images', target=get_next_images, args=([currentLeftPage]))
t.start()

window.mainloop()


#todo:
# Rudimentarilly done: Incorporate websocket connections so you can go to a website on your phone, push a button, send a websocket message to this python app, and turn the page, etc.
# Set up calibreweb to have a link which tells this app to run with the book from calibreweb loaded
#     Probably this link should open a new page which is the control page on the phone, even as it runs this app with the given book.
# Garbage collection: periodically check and see how much space is taken up by books, and delete the longest-ago-read books if too much space has been used
# Make this app more resilient--handle errors, check file names to make sure they are right/ok, make sure it runs cross-platform
# Put it on the raspberry pi
# Read some books!
# Make it run it with epubs and other formats
#      Will need more controls for things like changing font size
# Find a way to keep track of which pages have been read, and come back to where you left off last time when you re-open a book
# Set it up to have only one page open at a time instead of two if needed