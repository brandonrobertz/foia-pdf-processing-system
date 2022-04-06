#!/usr/bin/env python
import os
import subprocess

from django.core.management.base import BaseCommand
import tablib

from documents.models import Agency, Document, ProcessedDocument


# Don't steal focus while PDF->Texting
os.environ["JAVA_TOOL_OPTIONS"] = "-Djava.awt.headless=true"


class Command(BaseCommand):
    help = """
    Take awaiting-reading document with OCR'd PDF processed documents
    and create an auto-extracted processed document of it. Until the
    NLP side of things is working, this will just be the document text.

    NOTE: This only applies to non-complete documents without a CSV
    processed document!

    NOTE: The status here (going from awaiting-reading to auto-extracted)
    is also related to the delete_autoextractions mgmt command, so any
    status changes here need to be reflected over there, too.
    """
    DOCUMENT_TEXT_PROG = lambda _, inp_file: [
        "java",
        "-jar",
        "../pdf_to_text_snowtide/target/PDFtoTextSnowtide-uber.jar",
        inp_file,
        "0.5"
    ]

    def has_unacceptable_pdoc(self, pdocs):
        """
        A test to see if any of the pdocs have disallowed extensions.
        We use this to ensure we're operating on a Document that is a
        candidate for auto-CSV. Examples of Documents that we shouldn't
        attempt to auto-CSV would be ones that already have a CSV and
        we would return True here.
        """
        acceptable_pdoc_extensions = [
            ".ocr.pdf",
            # if we see this, we'll overwrite it
            ".auto.csv",
        ]
        for pdoc in pdocs:
            bad = True 
            for ext in acceptable_pdoc_extensions:
                if pdoc.file.name.endswith(ext):
                    bad = False
                    break
            if bad:
                return True
        return False

    def should_continue(self):
        yn = input("Continue? [Y]es/(n)o/(a)ll ").lower()
        if yn == "n":
            sys.exit(1)
        elif yn == "a":
            self.prompt = False

    def handle(self, *args, **options):
        self.prompt = True
        failures = []

        agencies = Agency.objects.all()
        # agencies = Agency.objects.filter(
        #     name="Aberdeen Police Department"
        # )
        for agency in agencies:
            print("Agency", agency)

            agency_unprocessed_docs = Document.objects.filter(
                status__in=[
                    "auto-extracted",
                    "awaiting-reading",
                    "awaiting-extraction",
                    "case-doc",
                ],
                file__endswith=".pdf",
                processeddocument__file__endswith=".ocr.pdf",
                # skip these, they don't have data, even if marked complete
                no_new_records=False,
                agency=agency,
            )
            print(f"{agency_unprocessed_docs.count()} candidate Documents")

            for doc in agency_unprocessed_docs:
                print("Document", doc)

                pdocs = doc.processeddocument_set.all()
                if self.has_unacceptable_pdoc(pdocs):
                    print("Skipping bad auto-CSV candidate Document.")

                ocr_pdoc = pdocs.filter(file__endswith=".ocr.pdf").first()

                print("Getting document text...")
                result = subprocess.run(
                    self.DOCUMENT_TEXT_PROG(ocr_pdoc.file.path),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                if result.returncode != 0:
                    print("Bad return code:", result.returncode)
                    print("PDF File:", doc.file.path)
                    failures.append(doc.file.path)
                    if self.prompt:
                        self.should_continue()
                    continue

                print(f"PDF to Text result: {len(result.stdout)} bytes")

                # TODO: build a real auto-CSV
                document_text = [{
                    "document_text": result.stdout
                }]

                # get path and filename w/o extension, so we can
                # tack on .auto.csv and get a final auto-CSV path
                pdf_basepath_noext = doc.file.path.replace(".pdf", "")
                # we're going to write to this one
                auto_csv_abspath = f"{pdf_basepath_noext}.auto.csv"
                print("Absolute auto-CSV path", auto_csv_abspath)
                pdf_relpath_noext = doc.file.name.replace(".pdf", "")
                # and set the .file = this, since they both point
                # to the same thing we should be good
                auto_csv_relpath = f"{pdf_relpath_noext}.auto.csv"
                print("Relative auto-CSV path", auto_csv_relpath)

                headers = document_text[0].keys()
                print("auto-CSV headers:", headers)
                csv = tablib.Dataset(headers=headers)
                for row in document_text:
                    values = list(row.values())
                    print(f"Appending row with {len(values)} columns")
                    csv.append(values)

                print(f"Built auto-CSV with {len(csv)} rows")

                with open(auto_csv_abspath, "w") as f:
                    f.write(csv.csv)

                # create existing auto.csv, if it doesnt exist
                existing_auto_csv = pdocs.filter(file__endswith=".auto.csv").first()
                if not existing_auto_csv:
                    print("Creating auto-CSV processed document")
                    existing_auto_csv = ProcessedDocument.objects.create(
                        document=doc,
                        status="auto-extracted"
                    )

                print("Auto-CSV processed document:", existing_auto_csv)

                existing_auto_csv.file = auto_csv_relpath
                existing_auto_csv.save()

                if self.prompt:
                    self.should_continue()

        print("Auto-CSV complete!")

        if failures:
            print("Failures:")
            for file in failures:
                print(file)
