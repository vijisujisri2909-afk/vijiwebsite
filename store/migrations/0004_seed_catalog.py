from django.db import migrations, models
import django.db.models.deletion


CATALOG = (
    (
        "claw-clips",
        "Claw Clips",
        (
            ("Pink Big Claw", 149, 199, "Pink", True, "The big, pretty claw clip that turns your everyday updo into a moment."),
            ("Cream Matte Claw", 199, 249, "Cream", True, "A dreamy matte finish and a comfy hold for your favorite hairstyles."),
            ("Glossy Beige Claw", 129, 179, "Beige", False, "A glossy neutral claw clip that goes with absolutely everything."),
        ),
    ),
    (
        "scrunchies",
        "Scrunchies",
        (
            ("Pink Satin Scrunchie", 79, 99, "Pink", True, "A silky-soft satin scrunchie that is gentle on your hair and cute on your wrist."),
            ("Velvet Brown Scrunchie", 89, 119, "Brown", True, "Soft, rich velvet for an easy little touch of cozy."),
            ("Floral Scrunchie", 99, 129, "Floral", False, "A sweet floral print for soft, sunny-day hair."),
        ),
    ),
    (
        "bow-clips",
        "Bow Clips",
        (
            ("Pearl Bow Clip", 119, 149, "Pearl", True, "A delicate bow with pearl details for a little extra sparkle."),
            ("Satin Pink Bow", 99, 129, "Pink", True, "A soft satin bow that makes every ponytail feel special."),
            ("White Bow Clip", 89, 109, "White", False, "A classic little white bow, ready for your everyday rotation."),
        ),
    ),
    (
        "mini-clips",
        "Mini Clips",
        (
            ("Daisy Mini Clips (Pack of 5)", 149, 199, "White", True, "Five tiny daisy clips for playful styles, half-up dos and everything in between."),
            ("Pearl Mini Clips", 129, 169, "Pearl", True, "Tiny pearl details to pin back those little flyaways in style."),
            ("Heart Mini Clips", 99, 129, "Pink", False, "Little heart-shaped clips for a cute finishing touch."),
        ),
    ),
)


def seed_catalog(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    database = schema_editor.connection.alias

    categories = {}
    for slug, name, _products in CATALOG:
        category, _ = Category.objects.using(database).get_or_create(
            slug=slug, defaults={"name": name}
        )
        categories[slug] = category

    for product in Product.objects.using(database).filter(category__isnull=True):
        product.category = categories["claw-clips"]
        product.save(update_fields=("category",))

    for product in Product.objects.using(database).all():
        image_name = str(product.image)
        if image_name.lower().startswith(("http://", "https://")):
            product.image = ""
            product.save(update_fields=("image",))

    for slug, _category_name, products in CATALOG:
        for name, price, original_price, color, trending, description in products:
            Product.objects.using(database).get_or_create(
                name=name,
                defaults={
                    "price": price,
                    "original_price": original_price,
                    "category": categories[slug],
                    "color": color,
                    "is_trending": trending,
                    "stock": 50,
                    "description": description,
                    "image": "",
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0003_category_alter_product_options_product_color_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="products",
                to="store.category",
            ),
        ),
    ]
