from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (NodeViewSet, TripViewSet, CarpoolRequestViewSet, 
                    OfferViewSet, driver_dashboard, WalletViewSet, TransactionViewSet)

router = DefaultRouter()
router.register(r'nodes', NodeViewSet)
router.register(r'trips', TripViewSet)
router.register(r'requests', CarpoolRequestViewSet)
router.register(r'offers', OfferViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'transactions', TransactionViewSet)

urlpatterns = [
    path('dashboard/', driver_dashboard, name='driver_dashboard'),
    path('', include(router.urls)),
]
