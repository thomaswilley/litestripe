# Generated by Django 5.1.1 on 2024-12-07 20:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('litestripe', '0002_rename_event_payload_orphanedpayment_event_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orphanedpayment',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
