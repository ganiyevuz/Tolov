from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymenttransaction",
            name="gateway",
            field=models.CharField(
                choices=[
                    ("payme", "Payme"),
                    ("click", "Click"),
                    ("uzum", "Uzum"),
                    ("paynet", "Paynet"),
                    ("octo", "Octo"),
                    ("multicard", "Multicard"),
                ],
                max_length=10,
            ),
        ),
    ]
