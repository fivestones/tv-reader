import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import Canvas
from tkinter import PhotoImage

# Open the PDF file using PyMuPDF
import fitz

# Function to open a PDF file and display the first two pages side by side
def display_pdf():
    # Open a file dialog to select a PDF file
    filepath = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])

    # Open the PDF file using PyMuPDF
    pdf_doc = fitz.open("blizzard.pdf")

    # Get the first two pages of the PDF
    page1 = pdf_doc[0]
    page2 = pdf_doc[1]

    # Render the pages as images using PyMuPDF's built-in rendering function
    zoom = 2  # Set the zoom level (2 is double size)
    mat = fitz.Matrix(zoom, zoom)  # Create a matrix to specify the zoom
    pix1 = page1.get_pixmap(matrix=mat)  # Render the page as an image
    pix2 = page2.get_pixmap(matrix=mat)  # Render the page as an image

    # Convert the images to PhotoImage objects for display in tkinter
    page1_image = PhotoImage(data = pix1.tobytes("ppm"),width=pix1.width, height=pix1.height)
    # page1_image.put(list(pix1.samples))

    page2_image = PhotoImage(data = pix2.tobytes("ppm"), width=pix2.width, height=pix2.height)
    # page2_image.put(list(pix2.samples))

    # Create a tkinter canvas and place it in the main window
    canvas = tk.Canvas(root, width=1200, height=600)
    canvas.pack()

    # Add the images to the canvas side by side
    canvas.create_image(0, 0, image=page1_image, anchor=tk.NW)
    canvas.create_image(600, 0, image=page2_image, anchor=tk.NW)

# Create the main window
root = tk.Tk()
root.title("PDF Viewer")

# Create a button to open a PDF file
# button = ttk.Button(root, text="Open PDF", command=display_pdf)
# button.pack()

display_pdf()

# Run the main loop
root.mainloop()
