from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("votaciones", "0005_voter_blockchain_address"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidate",
            name="image_url",
            field=models.ImageField(blank=True, null=True, upload_to="candidates/"),
        ),
    ]
