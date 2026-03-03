from tkinter import *
import fitz
root = Tk()
canvas = Canvas(root, width = 1200, height = 600)
canvas.pack()
doc=fitz.open("blizzard.pdf")

# img = PhotoImage(file="picture.ppm")

# pix1 = doc[0].get_pixmap()
# imgdata = doc[0].get_pixmap().tobytes("ppm")
# tkimg = PhotoImage(data = doc[0].get_pixmap().tobytes("ppm"))

img = PhotoImage(data = doc[0].get_pixmap().tobytes("ppm"))
canvas.create_image(0, 0, anchor=NW, image=img)
mainloop()