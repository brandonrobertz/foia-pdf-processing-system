from django.core.files.storage import FileSystemStorage


class OverwritingFileSystemStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        return name
