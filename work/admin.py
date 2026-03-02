from django.contrib import admin
from .models import Category, HelpRequest, Application, Notification, Payment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'color')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(HelpRequest)
class HelpRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'posted_by', 'category', 'urgency', 'status', 'budget', 'deadline', 'created_at')
    list_filter = ('status', 'urgency', 'category')
    search_fields = ('title', 'description')
    raw_id_fields = ('posted_by', 'selected_helper')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'help_request', 'status', 'proposed_budget', 'created_at')
    list_filter = ('status',)
    raw_id_fields = ('applicant', 'help_request')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    raw_id_fields = ('recipient',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'payer', 'payee', 'amount', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('payer__username', 'payee__username', 'transaction_id')
    raw_id_fields = ('payer', 'payee', 'help_request')
    readonly_fields = ('transaction_id',)
