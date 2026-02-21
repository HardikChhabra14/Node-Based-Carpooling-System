from rest_framework import serializers
from .models import Node, Edge, Trip, CarpoolRequest, Offer, Wallet, Transaction
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__'

class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = '__all__'

class TripSerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['driver', 'passed_nodes', 'created_at']

class CarpoolRequestSerializer(serializers.ModelSerializer):
    passenger = UserSerializer(read_only=True)
    class Meta:
        model = CarpoolRequest
        fields = '__all__'
        read_only_fields = ['passenger', 'created_at']

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = '__all__'
        read_only_fields = ['status']

class WalletSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Wallet
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
