# mock_files
"""
This module wraps the fs_database with a system that emulates a file system for testing purposes.

You can use it to create a real fs_database or a mock file system. However, remember the subtle
differences between a file system and the file tracking database. The file tracking database retains
a record of all files it has seen, even if they have been deleted or renamed.

For example:
1. Create a file in real life
2. Scan the directory where the file lives - it will be added to the database with its last-seen timestamp
3. Delete the file in real life
4. Scan again - the file's record remains in the database

To create an fs_database that includes sightings of deleted files, you should:
1. Create a mock file object
2. Create the file you want in it
3. Scan it into the database
4. Delete the file
5. Scan the mock_file object into the database again

Mock file objects can be created from an fs_database SQLite file and also stored as one.
"""
from ..fs_database import FSDatabase

class MockFiles:
    def __init__(self, db_path):
        super(db_path)
        # see if Anything is mounted under the C Then set this to be the default  Current working directory Otherwise find the drive with the lowest letter
        if
