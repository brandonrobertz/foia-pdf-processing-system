#!/usr/bin/env python
import json
import os
import re
import yaml

from django.core.management.base import BaseCommand
import sqlite3
import sqlite_utils

from documents.models import Agency, Document, ProcessedDocument


class Command(BaseCommand):
    help = """
    Export a metadata.yml (just the databases part) and a Sqlite DB
    containing information about the agency, link to the the DB, request
    status and information about data quality:
        - if we have officer names
        - if we have full case documents
        - if we have incident details
    """
    def add_arguments(self, parser):
        parser.add_argument(
            'output_data_dir',
            type=str,
            help=(
                "Path to Datasette directory to write metadata.dbs.yml "
                "and _Agencies.DB out to."
            )
        )
        parser.add_argument(
            '--wipe-db',
            action="store_true",
            help=("Use this to wipe out the agencies metadata DB before running.")
        )

    def db_url_from_agency(self, agency):
        # NOTE: if this changes, change export_sqlite_dbs
        # db_filepath_from_agency function as well
        agency_dbname = re.sub(r"[\s\.]+", "_", agency.name.replace("'", ""))
        # Datasette URL
        return os.path.join(f"/{agency_dbname}")

    def handle(self, *args, **options):
        output_data_dir = options["output_data_dir"]
        wipe = options.get("wipe_db")

        # output file paths
        agencies_meta_yml = os.path.join(output_data_dir,
                                         "_metadata.databases.yml")
        agencies_meta_db = os.path.join(output_data_dir,
                                        "0_agencies_metadata.db")

        metadata = {
            "databases": {}
        }

        if wipe and os.path.exists(agencies_meta_db):
            os.remove(agencies_meta_db)

        db = sqlite_utils.Database(sqlite3.connect(agencies_meta_db))

        for agency in Agency.objects.order_by("name"):
            url = self.db_url_from_agency(agency)
            db["agencies"].insert({
                "agency": f'<a href="{url}">{agency.name}</a>',
                "request_complete": agency.request_done,
                "processing_complete": agency.completed,
                "have_officer_names": agency.have_officer_names,
                "have_uof": agency.have_uof,
                "have_complaints": agency.have_complaints,
                "have_structured_data": agency.have_structured_data,
                "have_incident_summaries": agency.have_incident_summaries,
                "have_full_incident_documents": agency.have_full_incident_documents,
                "notes": agency.notes_html,
            }, pk="db")
            db_name = f"{url[1:]}"

            def yn(value):
                if value is None:
                    return 'Not specified'
                # return '✅' if value else '❌'
                return '&#x2705;' if value else '&#x274C;'

            description_html = re.sub(r"\s+", " ", f"""
            <table>
                <tr>
                    <td>Request complete:</td> <td>{yn(agency.request_done)}</td>
                </tr>
                <tr>
                    <td>Processing complete:</td> <td>{yn(agency.completed)}</td>
                </tr>
                <tr>
                    <td>Have officer names:</td> <td>{yn(agency.have_officer_names)}</td>
                </tr>
                <tr>
                    <td>Have UOF (regardless of disposition):</td> <td>{yn(agency.have_uof)}</td>
                </tr>
                <tr>
                    <td>Have complaints (regardless of disposition):</td> <td>{yn(agency.have_complaints)}</td>
                </tr>
                <tr>
                    <td>Have structured data (Excel, CSV, etc):</td> <td>{yn(agency.have_structured_data)}</td>
                </tr>
                <tr>
                    <td>Have incident summaries:</td> <td>{yn(agency.have_incident_summaries)}</td>
                </tr>
                <tr>
                    <td>Have full incident documents:</td> <td>{yn(agency.have_full_incident_documents)}</td>
                </tr>
            </table>""".replace("\n", ""))

            if agency.notes_html:
                description_html += f"""<br/>
                    <div>
                    <span style='font-weight: bold; font-size: 1.2em;'>Notes</span><br/>
                        {agency.notes_html}
                    </div>"""

            metadata["databases"][db_name] = {
                "title": agency.name,
                "description_html": description_html,
            }

        with open(agencies_meta_yml, "w") as f:
            f.write(yaml.dump(metadata, indent=2))
