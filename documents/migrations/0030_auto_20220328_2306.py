# Generated by Django 3.1.2 on 2022-03-28 23:06

from django.db import migrations
import markdownfield.models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0029_auto_20220328_2245'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agency',
            name='notes',
            field=markdownfield.models.MarkdownField(blank=True, default='', rendered_field='notes_html'),
        ),
    ]
