#!/usr/bin/env python
import os
import re
import subprocess

from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Take all auto-extracted documents, set them back to awaiting-reading
    and remove the associated auto.csv files. This is to be used in
    conjunction with autoextract_case_documents mgmt command, so any
    status/etc changes need to be reflected here.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--agency', type=str,
            help='Only use handle data for this agency (based on agency folder)'
        )
        parser.add_argument(
            '--ignore', type=str,
            help='Ignore these agencies (comma separated)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Don't actually delete anything, do a test run"
        )

    def double_check(self, msg):
        """
        Prompt the user with a message, but only do it once if
        they respond with A (all).
        """
        if not hasattr(self, "checked"):
            self.checked = {}

        # check to see if we already double checked
        # and they responded with (a)ll
        if self.checked.get(msg) == 'a':
            return True

        yna = input(f"{msg} (y)es/(n)o/(a)ll: ").lower()
        if yna == "a":
            self.checked[msg] = yna
            return True
        elif yna == "y":
            return True
        return False

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")
        only_agency = options.get("agency")
        not_agencies = re.split(
            r"\s*,\s*",
            options.get("ignore", "") or ""
        )

        agencies = Agency.objects.all()

        if only_agency:
            agencies = agencies.filter(
                name=only_agency
            )

        if not_agencies:
            agencies = agencies.exclude(
                name__in=not_agencies
            )

        for agency in agencies:
            agency_autocsv_docs = Document.objects.filter(
                status="auto-extracted",
                file__endswith=".pdf",
                # skip these, they don't have data, even if marked complete
                no_new_records=False,
                agency=agency,
            )

            if not agency_autocsv_docs.count():
                continue

            print()
            print(f"Agency: {agency.name}")

            for document in agency_autocsv_docs:
                pdocs = ProcessedDocument.objects.filter(
                    document=document,
                    file__endswith=".auto.csv",
                )

                doc_file = os.path.basename(document.file.name)
                print(f" - `{doc_file}` ({document.status})")

                for pdoc in pdocs:
                    filename = os.path.basename(pdoc.file.name)
                    print(f"   - Deleting: `{filename}`")

                    if not default_storage.exists(pdoc.file.path):
                        print(f"   - File doesn't exist on disk, not deleting: {pdoc.file.path}")
                        continue

                    if not dry_run and self.double_check("Delete pdoc?"):
                        assert pdoc.file.path.endswith(".auto.csv")
                        default_storage.delete(pdoc.file.path)
                        pdoc.delete()

                print("   - Setting doc status to 'awaiting-reading'")
                if not dry_run and self.double_check("Set doc status?"):
                    document.status = "awaiting-reading"
                    document.save()
                    pass
