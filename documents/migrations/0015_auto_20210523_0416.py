# Generated by Django 3.1.2 on 2021-05-23 04:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0014_auto_20210315_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='agency',
            name='completed',
            field=models.BooleanField(default='False'),
        ),
        migrations.CreateModel(
            name='SyntheticDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completed', models.BooleanField(default='False', help_text='Is this document complete? Note: If this is checked then all the documents and processed documents linked are also considered complete.')),
                ('documents', models.ManyToManyField(help_text='The original document(s) this file was based on', to='documents.Document')),
                ('processed_documents', models.ManyToManyField(help_text='The processed document(s) this file was based on', to='documents.ProcessedDocument')),
            ],
        ),
    ]
