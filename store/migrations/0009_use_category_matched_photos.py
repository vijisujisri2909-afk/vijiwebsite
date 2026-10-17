from django.db import migrations


PRODUCT_PHOTOS = {
    "Big Matte Pink Claw Clip": (
        "https://images.pexels.com/photos/20166056/pexels-photo-20166056/"
        "free-photo-of-hair-clips-on-white-background.jpeg?w=500"
    ),
    "Korean Cream Claw": (
        "https://images.pexels.com/photos/13865070/pexels-photo-13865070.jpeg?w=500"
    ),
    "Tortoise Brown Claw": (
        "https://images.pexels.com/photos/20166053/pexels-photo-20166053/"
        "free-photo-of-hair-clip-close-up.jpeg?w=500"
    ),
    "Clear Small Claw Set": (
        "https://images.pexels.com/photos/18421514/pexels-photo-18421514/"
        "free-photo-of-hair-clips-on-bed.jpeg?w=500"
    ),
    "Pink Satin Scrunchie": (
        "https://images.pexels.com/photos/6044135/pexels-photo-6044135.jpeg?w=500"
    ),
    "Velvet Red Scrunchie": (
        "https://images.pexels.com/photos/6983530/pexels-photo-6983530.jpeg?w=500"
    ),
    "Floral Cotton Scrunchie": (
        "https://images.pexels.com/photos/30284737/pexels-photo-30284737/"
        "free-photo-of-elegant-chiffon-scrunchie-on-designer-bag.jpeg?w=500"
    ),
    "Silk Beige Scrunchie": (
        "https://images.pexels.com/photos/10064224/pexels-photo-10064224.png?w=500"
    ),
    "Pearl Bow Clip": (
        "https://images.pexels.com/photos/33158725/pexels-photo-33158725/"
        "free-photo-of-portrait-of-woman-with-braided-hair-outdoors.png?w=500"
    ),
    "Black Velvet Bow": (
        "https://images.pexels.com/photos/14360411/pexels-photo-14360411.jpeg?w=500"
    ),
    "Daisy Mini Clip Set": (
        "https://images.pexels.com/photos/6188294/pexels-photo-6188294.jpeg?w=500"
    ),
    "Star Mini Clips": (
        "https://images.pexels.com/photos/6974031/pexels-photo-6974031.jpeg?w=500"
    ),
}


def update_product_photos(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    database = schema_editor.connection.alias

    for name, image_url in PRODUCT_PHOTOS.items():
        updated = Product.objects.using(database).filter(name=name).update(
            image_url=image_url
        )
        if updated != 1:
            raise RuntimeError(
                f"Expected exactly one catalog product named {name!r}, "
                f"updated {updated}."
            )


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0008_replace_catalog_with_twelve_products"),
    ]

    operations = [
        migrations.RunPython(update_product_photos, migrations.RunPython.noop),
    ]
