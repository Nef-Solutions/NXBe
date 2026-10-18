from django.contrib import admin
from .models import HomeZone, TradeCategory, Specialty, ProfessionalTrade

@admin.register(HomeZone)
class HomeZoneAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(TradeCategory)
class TradeCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'keywords')
    search_fields = ('name', 'keywords')
    filter_horizontal = ('home_zones',)

@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')
    list_filter = ('category',)
    search_fields = ('name', 'category__name')
    filter_horizontal = ('professionals',)


@admin.register(ProfessionalTrade)
class ProfessionalTradeAdmin(admin.ModelAdmin):
    list_display = ('professional', 'category', 'years_experience', 'certification_verified', 'is_active')
    list_filter = ('certification_verified', 'is_active', 'category')
    search_fields = ('professional__user__email', 'category__name')