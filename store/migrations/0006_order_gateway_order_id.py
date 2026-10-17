from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0005_checkout_payments"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="gateway_order_id",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
