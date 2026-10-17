from django.conf import settings
from django.db import models
import secrets


def generate_order_id():
    for _attempt in range(100):
        candidate = f"{secrets.randbelow(900000) + 100000}"
        if not Order.objects.filter(order_id=candidate).exists():
            return candidate
    raise RuntimeError("Could not generate a unique six-digit order ID.")


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ("id",)
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.IntegerField()
    original_price = models.IntegerField(default=0)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    image_url = models.URLField(
        max_length=500,
        blank=True, null=True, help_text="Use external URL"
    )
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    color = models.CharField(max_length=30, default="Pink")
    is_trending = models.BooleanField(default=False)
    stock = models.IntegerField(default=50)
    description = models.TextField()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        image_source = self.image_url or self.image.name or "no image"
        return f"{self.name} ({image_source})"

    @property
    def discount(self):
        return max(self.original_price - self.price, 0)

    @property
    def has_uploaded_image(self):
        return bool(self.image and self.image.storage.exists(self.image.name))


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="shopping_carts",
    )
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.pk}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("cart", "product"), name="unique_product_per_cart"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity


class Order(models.Model):
    class OrderStatus(models.TextChoices):
        PLACED = "placed", "Placed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on delivery"
        UPI = "upi", "UPI"
        RAZORPAY = "razorpay", "Razorpay / card (mock)"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_orders",
    )
    order_id = models.CharField(max_length=6, unique=True, editable=False)
    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    pincode = models.CharField(max_length=10, default="")
    city = models.CharField(max_length=80, default="")
    state = models.CharField(max_length=80, default="Tamil Nadu")
    landmark = models.CharField(max_length=120, blank=True)
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    gateway_order_id = models.CharField(max_length=80, blank=True, default="")
    order_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PLACED
    )
    total_amount = models.PositiveIntegerField()
    payment_proof = models.ImageField(upload_to="payment-proofs/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order #{self.order_id} — {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = generate_order_id()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.customer_name

    @property
    def total(self):
        return self.total_amount

    @property
    def status(self):
        return self.order_status

    @property
    def delivery_address(self):
        parts = [self.address, self.landmark, self.city, self.state, self.pincode]
        return ", ".join(part for part in parts if part)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True
    )
    product_name = models.CharField(max_length=100)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
