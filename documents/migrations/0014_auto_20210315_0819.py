# Generated by Django 3.1.2 on 2021-03-15 08:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0013_auto_20201129_0719'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(choices=[('complete', 'Complete'), ('awaiting-cleaning', 'Awaiting final cleaning'), ('awaiting-csv', 'Awaiting conversion to CSV'), ('awaiting-reading', 'Awaiting reading/processing'), ('awaiting-extraction', 'Awaiting extraction'), ('non-request', 'Misc file/unrelated to response'), ('exemption-log', 'Exemption log'), ('unchecked', 'New/Unprocessed')], default='unchecked', help_text='Status of processing the response document', max_length=30),
        ),
        migrations.AlterField(
            model_name='processeddocument',
            name='status',
            field=models.CharField(choices=[('complete', 'Complete'), ('awaiting-cleaning', 'Awaiting final cleaning'), ('awaiting-csv', 'Awaiting conversion to CSV'), ('awaiting-reading', 'Awaiting reading/processing'), ('awaiting-extraction', 'Awaiting extraction'), ('non-request', 'Misc file/unrelated to response'), ('exemption-log', 'Exemption log'), ('unchecked', 'New/Unprocessed')], default='unchecked', help_text='Status of processing the response document', max_length=30),
        ),
    ]
