from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('screening', '0003_candidateapplication_field_of_study_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='hrprofile',
            name='company',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
    ]
