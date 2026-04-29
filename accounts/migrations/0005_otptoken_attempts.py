from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_otptoken_delete_emailverificationtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='otptoken',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
