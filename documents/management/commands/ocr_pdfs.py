#!/usr/bin/env python
import os
import shutil
import subprocess

from django.core.management.base import BaseCommand

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    OCR PDFs that haven't been OCR'd already and set them to awaiting-reading.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            '--pre-ocr-folder', type=str,
            help='Check in this folder for already OCRd PDFs'
        )

    def handle(self, *args, **options):
        pre_ocr_folder = options.get('pre_ocr_folder')
        # basename => filepath
        pre_ocr_files = {}
        if pre_ocr_folder:
            for file in os.listdir(pre_ocr_folder):
                # look for either acceptable OCRd extenaion
                if file.endswith(".ocr-pdf") or file.endswith(".ocr.pdf"):
                    # convert the lookup to the assumed lookup extension, leave
                    # the filepath the real extension though
                    key = file.replace(".ocr-pdf", ".ocr.pdf")
                    pre_ocr_files[key] = os.path.join(pre_ocr_folder, file)

        prompt = True
        failures = []
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
                pdf_input = doc.file.path
                basename = os.path.splitext(pdf_input)[0]
                ocr_output = f"{basename}.ocr.pdf"

                if pdf_input.endswith(".ocr.pdf"):
                    print("Skipping OCR'd document", pdf_input);
                    continue
                if os.path.exists(ocr_output):
                    print("OCR'd already complete", ocr_output);
                    continue
                pdocs = ProcessedDocument.objects.filter(
                    document=doc,
                    file__endswith=".ocr.pdf"
                )
                if pdocs.count():
                    print("OCR'd processed document already exists", ocr_output);
                    continue


                def create_pdoc(document, ocr_output):
                    pdoc = ProcessedDocument.objects.create(
                        document=document,
                        file=ocr_output,
                        status="awaiting-reading"
                    )
                    pdoc.save()

                    print("OCR complete!")
                    print(pdoc.file.path)
                    print(os.stat(pdoc.file.path))


                # look for pre-converted file first
                search = os.path.basename(ocr_output)
                if search in pre_ocr_files:
                    print("Found matching pre-OCR'd file", search)
                    print("Checking for dupes...", end=" ")
                    
                    # make sure this PDF file is uniquye to this agency
                    # since the pre-OCR'd files aren't grouped by agency
                    matches = Document.objects.filter(
                        file__endswith=os.path.basename(pdf_input)
                    )
                    print(f"found {matches.count()} files")

                    if matches.count() > 1:
                        print("Not copying match, can't ensure uniqueness of file.")
                    else:
                        ocr_path = pre_ocr_files[search]
                        print(f"Copying {ocr_path} to {ocr_output}")
                        shutil.copy(ocr_path, ocr_output)
                        create_pdoc(doc, ocr_output)
                        continue

                print("OCRing Document:", pdf_input)
                result = subprocess.run([
                    "ocrmypdf",
                    "--threshold",
                    "--remove-background",
                    "--unpaper-args=--no-grayfilter",
                    "--force-ocr",
                    "--clean-final",
                    "--remove-vectors",
                    "--oversample", "600",
                    "--tesseract-oem", "1",
                    "--tesseract-pagesegmode", "12",
                    pdf_input, ocr_output
                ])

                if result.returncode != 0:
                    print("Bad return code:", result.returncode)
                    print("PDF File:", pdf_input)
                    failures.append(pdf_input)
                    continue

                create_pdoc(doc, ocr_output)

                if prompt:
                   yn = input("Continue? [Y]es/(n)o/(a)ll ").lower()
                   if yn == "y":
                       continue
                   elif yn == "n":
                       break
                   elif yn == "a":
                       prompt = False
                       continue

        print("Conversion complete!")

        if failures:
            print("Failures:")
            for file in failures:
                print(file)
