# Generated by Django 5.2.3 on 2025-06-24 16:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_collecteddata_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='forensicsession',
            name='android_version',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='forensicsession',
            name='device_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='forensicsession',
            name='save_path',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
