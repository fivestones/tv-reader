from timeit import default_timer as timer
from PIL import ImageTk, Image
time = [timer()]
imageLeft = Image.open("pageImages/00.png")
time.append(timer())
imageRight = Image.open("pageImages/01.png")
time.append(timer())
print (time)
print("total time: " + str(time[len(time)-1]-time[0]))
timeOfEachPage = [t - s for s, t in zip(time[1:], time[2:])]
print("Average per page: " + str(sum(timeOfEachPage)/len(timeOfEachPage)))
print("Load pdf time: " + str(time[1]-time[0]))