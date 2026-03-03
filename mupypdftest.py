import fitz
from PIL import Image, ImageTk

doc = fitz.open("blizzard.pdf")


for page in doc.pages(0,1):
    pix = page.get_pixmap()
    mode = "RGBA" if pix.alpha else "RBG"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    tkimg = ImageTk.PhotoImage(img)
