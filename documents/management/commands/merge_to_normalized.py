#!/usr/bin/env python
import os
import re

from django.core.management.base import BaseCommand

from documents.models import Agency, Document


def std_filename(filename):
    return re.sub(".*/?agency_attachments/", "agency_attachments/", filename)


class Command(BaseCommand):
    help = """
    Merge one or more documents into a single, "standardized" CSV file.
    This program accepts document paths as input. These are looked up,
    by file name, in the DB, checked to see if the CSV headers are matched
    and all files can be clearly merged.
    """

    def add_arguments(self, parser):
        parser.add_argument("document_path", type=str, nargs="+")
        # parser.add_argument(
        #     "--agency", type=str,
        #     help="Only use handle data for this agency (based on agency folder)"
        # )

    def handle(self, *args, **options):
        matches = []
        agency = None
        for raw_filename in options["document_path"]:
            if not os.path.exists(raw_filename):
                raise Exception(f"File does not exist: {raw_filename}")

            standardized = std_filename(raw_filename)
            print(f"Searching for Document by path: {raw_filename}")
            print(f" - Standardized: {standardized}")

            matched_docs = Document.objects.filter(
                file__endswith=standardized
            )

            assert matched_docs.count(), "No documents matching file!"

            for doc in matched_docs:
                matches.append(doc)
                if agency is None:
                    agency = doc.agency
                assert doc.agency.name == agency.name, "Agency mismatch!"

        print("Agency", agency)
        print(matches)
