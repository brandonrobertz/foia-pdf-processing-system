#!/usr/bin/env python
import os
import shutil

from django.core.management.base import BaseCommand
from django.conf import settings
from pdf2image import convert_from_path

from documents.models import Agency, ProcessedDocument


class Command(BaseCommand):
    help = """
    Find OCR'd case documents and allow us to segment them into individual
    cases/incidents. This will skip documents with a single page.
    """

    def handle(self, *args, **options):
        pdoc_images = []
        total_pages = 0
        for agency in Agency.objects.all():
            pdocs = ProcessedDocument.objects.filter(
                file__endswith=".ocr.pdf",
                document__agency=agency,
                document__status__in=[
                    "awaiting-reading",
                    "auto-extracted",
                    "awaiting-extraction",
                    "case-doc",
                    "unchecked",
                ])

            for pdoc in pdocs:
                if not pdoc.file:
                    continue
                if not pdoc.file.path or not os.path.exists(pdoc.file.path):
                    continue

                print(f"Parsing: {pdoc}")

                pages = convert_from_path(pdoc.file.path, dpi=200)
                page_count = len(pages)

                pdoc.pages = page_count
                pdoc.save()

                if not page_count or page_count <= 1:
                    continue

                tmpdir = os.path.join(settings.MEDIA_ROOT, "wapd-segment-temp")

                # clear it (delete all files)
                if os.path.exists(tmpdir):
                    shutil.rmtree(tmpdir)

                os.makedirs(tmpdir)

                img_files = []
                for idx, page in enumerate(pages):
                    tmpfile_path = os.path.join(
                        tmpdir, f"page-{idx}.jpg"
                    )
                    page.save(tmpfile_path, "JPEG")
                    img_files.append(tmpfile_path)

                total_pages += len(img_files)
                pdoc_images.append({
                    "id": pdoc.id,
                    "file": pdoc.file.path,
                    "pages": img_files
                })

                print(f" - Pages: {len(img_files)}")

        print(f"Processed Documents: {len(pdoc_images)}")
        print(f"Total Pages: {total_pages}")
        print("Done")
