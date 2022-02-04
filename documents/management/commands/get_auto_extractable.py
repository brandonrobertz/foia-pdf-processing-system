#!/usr/bin/env python
from django.core.management.base import BaseCommand

from documents.models import Agency, Document


class Command(BaseCommand):
    help = """
    """

    def handle(self, *args, **options):
        def clean_name(filename):
            return filename.replace("agency_attachments/", "")

        for agency in Agency.objects.all():
            agency_unprocessed_docs = Document.objects.filter(
                status__in=[
                    "awaiting-reading",
                    "awaiting-extraction",
                    "case-doc",
                    "unchecked",
                ],
                file__endswith=".pdf",
                # skip these, they don't have data, even if marked complete
                no_new_records=False,
                agency=agency,
            )
            for doc in agency_unprocessed_docs:
                print(doc.file.name.replace("agency_attachments/", ""))
