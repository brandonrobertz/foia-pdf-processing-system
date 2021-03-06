# Generated by Django 3.1.2 on 2021-05-23 08:08

from django.db import migrations, models
import documents.util


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0016_auto_20210523_0806'),
    ]

    operations = [
        migrations.AddField(
            model_name='syntheticdocument',
            name='file',
            field=models.FileField(blank=True, help_text='The file that we created.', max_length=500, null=True, upload_to=documents.util.document_file_path),
        ),
    ]
