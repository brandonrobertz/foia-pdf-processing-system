import json

from django.core.management.base import BaseCommand

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Import an agency notes text/markdown file and save them to the
    appropriate agency notes field. This will try to match an
    agency based on the H1 (#) field. Specifying the --wipe option
    will cause agency notes to be cleared before running. Duplicate
    notes fields will be appended as new paragraphs.
    """
    def add_arguments(self, parser):
        parser.add_argument(
            'input_notes_file',
            type=str,
            help="Path to input notes Markdown file"
        )
        parser.add_argument(
            '--wipe',
            action="store_true",
            help=(
                "Clear all agency notes for all agencies found, BEFORE making "
                "any changes. Without this option, notes will be appended."
            )
        )

    def parse_notes_file(self, input_notes_file):
        # agency_name => {agency: ..., notes: "..."}
        agency_notes = {}
        with open(input_notes_file, "r") as f:
            lines = f.readlines()

        prev_agency = None
        for line in lines:
            print("Parsing line:", line)

            agency_name = None
            if line.startswith("#"):
                agency_name = line.split(" ", 1)[1].strip().replace(
                    "PD", "Police Department"
                ).replace(":", "").replace("’", "'")

                print("Extracted agency name:", agency_name)

                # stupid fix
                if agency_name == "Central Washington University Police Department":
                    agency_name = "Central Washington University Washington Police Department"

                try:
                    agency = Agency.objects.get(name=agency_name)
                except Agency.DoesNotExist:
                    print(f"Couldn't find matching agency: '{agency_name}'")
                    agency_name = input("Enter correct name: ")
                    agency = Agency.objects.get(name=agency_name)

                assert agency, "Couldn't find agency! Fix the notes file. Stopping."

                prev_agency = agency_name
                if prev_agency not in agency_notes:
                    agency_notes[prev_agency] = {
                        "agency_id": agency.pk,
                        "notes": ""
                    }

            # text line
            else:
                agency_notes[prev_agency]["notes"] += line.replace(
                    "\u2019", "'"
                )

        return agency_notes

    def handle(self, *args, **options):
        input_notes_file = options["input_notes_file"]
        should_wipe = options.get("wipe")

        notes_dict = self.parse_notes_file(input_notes_file)
        print(json.dumps(notes_dict, indent=2))

        if should_wipe:
            for agency_name, notes_data in notes_dict.items():
                agency_id = notes_data["agency_id"]
                agency = Agency.objects.get(pk=agency_id)
                agency.notes = None
                agency.notes_html = None
                agency.save()

        for agency_name, notes_data in notes_dict.items():
            agency_id = notes_data["agency_id"]
            notes_md = notes_data["notes"]
            agency = Agency.objects.get(pk=agency_id)
            agency.notes = notes_md.strip()
            agency.save()
