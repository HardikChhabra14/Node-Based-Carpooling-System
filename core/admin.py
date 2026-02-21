from django.contrib import admin
from .models import Node, Edge, Trip, CarpoolRequest, Offer, Wallet, Transaction

@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ('from_node', 'to_node')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('driver', 'start_node', 'end_node', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(CarpoolRequest)
class CarpoolRequestAdmin(admin.ModelAdmin):
    list_display = ('passenger', 'pickup_node', 'dropoff_node', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('trip', 'request', 'fare', 'detour', 'status')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'trip', 'created_at')
    list_filter = ('transaction_type',)
