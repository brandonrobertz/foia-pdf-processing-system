from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    name = 'documents'

    def ready(self):
        """
        This runs when our app has all of its models registered, including
        django ones. So now we can run our signals, which depend on the
        models being registered.
        """
        import documents.signals
