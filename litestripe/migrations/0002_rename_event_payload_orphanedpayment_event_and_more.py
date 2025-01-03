# Generated by Django 5.1.1 on 2024-12-07 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('litestripe', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orphanedpayment',
            old_name='event_payload',
            new_name='event',
        ),
        migrations.AddField(
            model_name='orphanedpayment',
            name='reason',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
