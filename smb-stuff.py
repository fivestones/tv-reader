# import urllib #not needed???
import smbclient.shutil
import smbclient
import os
import threading
import time

# src = r"\\server.local\tv-bookreader\here.txt"
src = r"\\server.local\tv-bookreader\test.mobi"
des = r"test.mobi"
print(src)
smbclient.register_session("server.local", username="tv-bookreader", password="password")
print(smbclient.stat(src).st_size) #print the file size
# smbclient.shutil.copy2(source, "hereagain.txt")


def checker(source_path, destination_path, file_size):
    """
    Compare 2 files till they're the same and print the progress.

    :type source_path: str
    :param source_path: path to the source file
    :type destination_path: str
    :param destination_path: path to the destination file
    """

    # Making sure the destination path exists
    while not os.path.exists(destination_path):
        print("doesn't exist")
        time.sleep(.01)

    # Keep checking the file size till it's the same as source file
    while file_size != os.path.getsize(destination_path):
        print ("percentage {}".format(int((float(os.path.getsize(destination_path))/float(file_size)) * 100)), end="\r")
        time.sleep(.01)

    print ("percentage 100")

def copying_file(source_path, destination_path):
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

# Start the copying on a separate thread
t = threading.Thread(name='copying', target=copying_file, args=(src, des))
t.start()

# Checking the status of destination file on a separate thread
b = threading.Thread(name='checking', target=checker, args=(src, des, smbclient.stat(src).st_size))
b.start()