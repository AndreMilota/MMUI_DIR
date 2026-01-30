# this file is for testing the mock_files interface

from .mock_files import MockFiles
# import any other needed modules here


def test_1():
    # create a temporary directory to hold the mock file system
    virtual_fs = MockFiles("vsf_1.sqlite")
    # set the time to the first day of 2026 at noon UTC
    virtual_fs.set_fixed_time("2026-01-01T12:00:00Z")
    # mount c drive
    virtual_fs.mount_volume("C:\\")
    # put 5 text files in c:\test
    virtual_fs.add_directory("C:\\test")
    for i in range(5):
        virtual_fs.add_file(f"C:\\test\\file_{i}.txt", content=f"This is file {i}")
    # now list the files and print them
    file_list = virtual_fs.list_files("C:\\test")
    print("Files in C:\\test:")
    for f in file_list:
        print(f" - {f}")

if __name__ == "__main__":
    test_1()

