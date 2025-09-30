from django.contrib import admin
from .models import (
	ChatRoom, Message, Product, ProductImage, Category, SubCategory, Feature, ProductFeature, Review,
	Coupon, CouponRedemption
)

# title and site header
admin.site.site_title = "Oysloecore Admin"
admin.site.site_header = "Oysloecore Admin Portal"
admin.site.index_title = "Welcome to the Oysloecore Admin Portal"


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
	list_display = ('id', 'room_id', 'name', 'is_group', 'created_at')
	search_fields = ('name', 'room_id', 'members__email', 'members__name')
	list_filter = ('is_group', 'created_at')
	ordering = ('-created_at',)
	filter_horizontal = ('members',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'room', 'sender', 'short_content', 'is_read', 'created_at')
	search_fields = ('room__name', 'sender__email', 'sender__name', 'content')
	list_filter = ('is_read', 'created_at')
	ordering = ('-created_at',)

	def short_content(self, obj):
		return (obj.content[:50] + '...') if len(obj.content) > 50 else obj.content


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ('id', 'pid', 'name', 'category', 'price', 'created_at')
	search_fields = ('pid', 'name', 'description', 'category__name')
	list_filter = ('category', 'created_at')
	ordering = ('-created_at',)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
	list_display = ('id', 'product', 'created_at')
	search_fields = ('product__name', 'product__pid')
	list_filter = ('created_at',)
	ordering = ('-created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'created_at')
	search_fields = ('name', 'description')
	list_filter = ('created_at',)
	ordering = ('name',)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'category', 'created_at')
	search_fields = ('name', 'description', 'category__name')
	list_filter = ('category', 'created_at')
	ordering = ('name',)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'subcategory', 'created_at')
	search_fields = ('name', 'description', 'subcategory__name')
	list_filter = ('subcategory', 'created_at')
	ordering = ('name',)


@admin.register(ProductFeature)
class ProductFeatureAdmin(admin.ModelAdmin):
	list_display = ('id', 'product', 'feature', 'value', 'created_at')
	search_fields = ('product__name', 'product__pid', 'feature__name', 'value')
	list_filter = ('feature', 'product', 'created_at')
	ordering = ('-created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
	list_display = ('id', 'product', 'user', 'rating', 'created_at')
	search_fields = ('product__name', 'user__email', 'user__name', 'comment')
	list_filter = ('rating', 'created_at', 'product')
	ordering = ('-created_at',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
	list_display = ('id', 'code', 'discount_type', 'discount_value', 'uses', 'max_uses', 'is_active', 'valid_from', 'valid_until')
	search_fields = ('code', 'description')
	list_filter = ('discount_type', 'is_active', 'created_at')
	ordering = ('-created_at',)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'coupon', 'user', 'created_at')
	search_fields = ('coupon__code', 'user__email', 'user__name')
	list_filter = ('created_at',)
	ordering = ('-created_at',)
