import os

from django.core.files import locks
from django.core.files.move import file_move_safe
from django.core.files.storage import FileSystemStorage


class OverwritingFileSystemStorage(FileSystemStorage):
    OS_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | getattr(os, 'O_BINARY', 0)

    def get_available_name(self, name, max_length=None):
        return name

    def get_valid_name(self, name):
        return name

    def _save(self, name, content):
        """
        Overrides the normal save method except we want to overwrite
        files if they exist (the user updated/cleaned up an existing
        middle state file or some correction).
        """
        full_path = self.path(name)

        # Create any intermediate directories that do not exist.
        directory = os.path.dirname(full_path)
        try:
            if self.directory_permissions_mode is not None:
                # Set the umask because os.makedirs() doesn't apply the "mode"
                # argument to intermediate-level directories.
                old_umask = os.umask(0o777 & ~self.directory_permissions_mode)
                try:
                    os.makedirs(directory, self.directory_permissions_mode, exist_ok=True)
                finally:
                    os.umask(old_umask)
            else:
                os.makedirs(directory, exist_ok=True)
        except FileExistsError:
            raise FileExistsError('%s exists and is not a directory.' % directory)

        # This file has a file path that we can move.
        if hasattr(content, 'temporary_file_path'):
            file_move_safe(content.temporary_file_path(), full_path)

        # This is a normal uploadedfile that we can stream.
        else:
            # The current umask value is masked out by os.open!
            fd = os.open(full_path, self.OS_OPEN_FLAGS, 0o666)
            _file = None
            try:
                locks.lock(fd, locks.LOCK_EX)
                for chunk in content.chunks():
                    if _file is None:
                        mode = 'wb' if isinstance(chunk, bytes) else 'wt'
                        _file = os.fdopen(fd, mode)
                    _file.write(chunk)
            finally:
                locks.unlock(fd)
                if _file is not None:
                    _file.close()
                else:
                    os.close(fd)

        if self.file_permissions_mode is not None:
            os.chmod(full_path, self.file_permissions_mode)

        # Store filenames with forward slashes, even on Windows.
        return str(name).replace('\\', '/')
