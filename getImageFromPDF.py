import fitz
import os
from timeit import default_timer as timer
from threading import Thread
from time import sleep

def makeImages():
    global message
    time = [timer()]

    #load document
    message = "Loading document"
    print(message)
    doc = fitz.open("blizzard.pdf")
    message = "Loaded"
    print(message)


    global numPages
    global zeroPadding
    numPages = doc.page_count #get number of pages in the pdf
    zeroPadding = len("%i" % numPages) #find out how many zeros are needed to pad the page numbers with (how many digits in this number)

    if not os.path.exists("pageImages"):
        os.makedirs("pageImages")


    #iterate through pages of document and save each to a png file
    for page in doc:
        time.append(timer())
        sleep(0.1)
        page.get_pixmap().save("pageImages/" + str(page.number).zfill(zeroPadding) + ".png")
        message = "page %i" % page.number
        print(message)

    time.append(timer())

    #print(time)
    print("total time: " + str(time[len(time)-1]-time[0]))
    timeOfEachPage = [t - s for s, t in zip(time[1:], time[2:])]
    print("Average per page: " + str(sum(timeOfEachPage)/len(timeOfEachPage)))
    print("Load pdf time: " + str(time[1]-time[0]))

# message = ""
# print('Starting background task...')
# daemon = Thread(target=makeImages, daemon=True, name='makeImages')
# daemon.start()

# oldMessage = message

# print('Started background process to make images from PDF')
# while True:
#     if message != oldMessage:
#         print("Incomming message: " + message)
#         oldMessage = message
#     sleep(0.1)
# print ("done")