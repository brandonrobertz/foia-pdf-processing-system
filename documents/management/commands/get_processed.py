#!/usr/bin/env python
from django.core.management.base import BaseCommand

from documents.models import Agency, Document


class Command(BaseCommand):
    help = """
    """

    def handle(self, *args, **options):
        def clean_name(filename):
            return filename.replace("agency_attachments/", "")

        print("Document filename, Processed document filename, Status")
        for agency in Agency.objects.all():
            for doc in agency.document_set.all():
                for p_doc in doc.completed_files:
                    print(
                        clean_name(doc.file.name),
                        clean_name(p_doc.file.name),
                        p_doc.status
                    )
