# Generated by Django 5.2.3 on 2025-07-03 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0002_alter_forensicreport_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='forensicreport',
            options={},
        ),
        migrations.RemoveIndex(
            model_name='analysisresult',
            name='analysis_an_analysi_d1ccc8_idx',
        ),
        migrations.RemoveIndex(
            model_name='analysisresult',
            name='analysis_an_is_crit_0ba06e_idx',
        ),
        migrations.AlterField(
            model_name='analysisresult',
            name='analysis_type',
            field=models.CharField(choices=[('fraud', 'Fraude'), ('sentiment', 'Sentiment'), ('anomaly', 'Anomalie'), ('llm', 'Analyse LLM')], max_length=20),
        ),
    ]
