from django.contrib import admin

from .models import Cart, CartItem, Category, Order, OrderItem, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "image_url", "stock", "is_trending")
    list_filter = ("category", "is_trending")
    search_fields = ("name", "color", "description")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "customer_name",
        "phone",
        "total_amount",
        "payment_method",
        "payment_status",
        "order_status",
        "created_at",
    )
    list_filter = ("payment_method", "payment_status", "order_status", "created_at")
    search_fields = ("order_id", "customer_name", "phone")
    inlines = (OrderItemInline,)


admin.site.register((Cart, CartItem))
