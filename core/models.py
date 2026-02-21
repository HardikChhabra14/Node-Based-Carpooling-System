from django.db import models
from django.contrib.auth.models import User

class Node(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Edge(models.Model):
    from_node = models.ForeignKey(Node, related_name='outgoing_edges', on_delete=models.CASCADE)
    to_node = models.ForeignKey(Node, related_name='incoming_edges', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('from_node', 'to_node')

    def __str__(self):
        return f"{self.from_node} -> {self.to_node}"

class Trip(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    driver = models.ForeignKey(User, related_name='trips', on_delete=models.CASCADE)
    start_node = models.ForeignKey(Node, related_name='trips_starting', on_delete=models.CASCADE)
    end_node = models.ForeignKey(Node, related_name='trips_ending', on_delete=models.CASCADE)
    route = models.JSONField()  # Ordered list of node IDs
    current_node = models.ForeignKey(Node, related_name='current_trips', on_delete=models.SET_NULL, null=True, blank=True)
    passed_nodes = models.JSONField(default=list)  # List of node IDs already passed
    max_passengers = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip by {self.driver} from {self.start_node} to {self.end_node}"

class CarpoolRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    passenger = models.ForeignKey(User, related_name='requests', on_delete=models.CASCADE)
    pickup_node = models.ForeignKey(Node, related_name='pickups', on_delete=models.CASCADE)
    dropoff_node = models.ForeignKey(Node, related_name='dropoffs', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request by {self.passenger}: {self.pickup_node} -> {self.dropoff_node}"

class Offer(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    trip = models.ForeignKey(Trip, related_name='offers', on_delete=models.CASCADE)
    request = models.ForeignKey(CarpoolRequest, related_name='offers', on_delete=models.CASCADE)
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    detour = models.IntegerField()  # Number of extra nodes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"Offer for {self.request} by {self.trip.driver}"

class Wallet(models.Model):
    user = models.OneToOneField(User, related_name='wallet', on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Wallet: {self.user.username} - ${self.balance}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('TOPUP', 'Top-up'),
        ('FARE_PAYMENT', 'Fare Payment'),
        ('EARNING', 'Driver Earning'),
    ]
    wallet = models.ForeignKey(Wallet, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    trip = models.ForeignKey(Trip, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} ({self.wallet.user.username})"

# Signals to create wallet
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
