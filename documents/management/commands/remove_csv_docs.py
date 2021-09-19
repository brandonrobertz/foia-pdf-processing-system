#!/usr/bin/env python
import re
from django.core.management.base import BaseCommand

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Remove CSVs that got added as responsive documents in error.
    """
    SKIP_AGENCIES = [
        "Redmond Police Department",
        "Black Diamond Police Department",
        "West Richland Police Department",
    ]

    def yes_no(self, message, default=False):
        response = input(f"{message.strip()} ").strip().lower()
        if not response:
            return default
        return response.startswith("y")

    def handle(self, *args, **options):
        matches = []
        for doc in Document.objects.filter(file__endswith=".csv"):
            # if we marked the agency complete, don't mess with it
            if doc.agency.completed:
                continue
            # skip redmond, we actually got CSVs
            if doc.agency.name in self.SKIP_AGENCIES:
                continue
            # false positive (delete it!)
            if ".precleaned" in doc.file.name:
                continue

            print("\n====================")
            print("Agency:", doc.agency.name)
            print("Responsive document:", doc.file.name)
            nocsv = re.sub(".csv", "", doc.file.name)
            basepath = "/".join(nocsv.split("/")[:-1])

            filename = nocsv.split("/")[-1]
            # print("\t", "Raw filename:", filename)

            nosheet = "-".join(filename.split("-")[:-1]) or filename
            # print("\t", "Without sheet extension:", nosheet)

            start_pattern = f"{basepath}/{nosheet}"
            print("\t", f"Search pattern: `{start_pattern}`")

            possible_parents = Document.objects.filter(
                file__startswith=start_pattern
            ).exclude(pk=doc.pk)
            n_poss = possible_parents.count()
            print("----------")
            print(f"{n_poss} possible parent{'s' if n_poss != 1 else ''}:")
            for pp in possible_parents:
                print("  - ", pp.file.name)

            if n_poss == 1:
                print("It's recommended we delete this!")

            if self.yes_no("Delete doc? [Y/n]", default=True):
                doc.delete()
                print("Deleting.")
