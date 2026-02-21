from decimal import Decimal
from rest_framework import viewsets, status, decorators, serializers
from rest_framework.response import Response
from .models import Node, Edge, Trip, CarpoolRequest, Offer, Wallet, Transaction
from .serializers import (NodeSerializer, TripSerializer, CarpoolRequestSerializer, 
                           OfferSerializer, WalletSerializer, TransactionSerializer)
from .services import graph_service, fare_service
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm

class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    def perform_create(self, serializer):
        start_node = serializer.validated_data['start_node']
        end_node = serializer.validated_data['end_node']
        
        # Pathfinding
        route = graph_service.get_shortest_path(start_node.id, end_node.id)
        if not route:
            raise serializers.ValidationError("No path found between selected nodes.")
            
        serializer.save(driver=self.request.user, route=route, current_node=start_node)

    @decorators.action(detail=True, methods=['post'])
    def update_node(self, request, pk=None):
        trip = self.get_object()
        node_id = request.data.get('node_id')
        try:
            node = Node.objects.get(id=node_id)
        except Node.DoesNotExist:
            return Response({'error': 'Node not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        if node_id not in trip.route:
            return Response({'error': 'Node not in trip route'}, status=status.HTTP_400_BAD_REQUEST)
            
        trip.current_node = node
        if node_id not in trip.passed_nodes:
            trip.passed_nodes.append(node_id)
        trip.save()
        return Response(TripSerializer(trip).data)

    @decorators.action(detail=True, methods=['get'])
    def matching_requests(self, request, pk=None):
        trip = self.get_object()
        # Remaining route: nodes from current_node onwards
        try:
            curr_idx = trip.route.index(trip.current_node.id)
            remaining_route = trip.route[curr_idx:]
        except (ValueError, AttributeError):
            remaining_route = trip.route
            
        # Filter pending requests
        pending_requests = CarpoolRequest.objects.filter(status='PENDING')
        matches = []
        
        for req in pending_requests:
            # Check if pickup and dropoff within 2 nodes of remaining route
            if graph_service.is_within_radius(remaining_route, req.pickup_node.id) and \
               graph_service.is_within_radius(remaining_route, req.dropoff_node.id):
                
                # Calculate detour and fare
                new_route, detour = graph_service.calculate_best_detour(remaining_route, req.pickup_node.id, req.dropoff_node.id)
                if new_route:
                    # For fare, we'd need occupancy. For now assume basic.
                    # occupancy = trip.get_occupancy_per_hop(new_route) # TODO
                    fare = fare_service.calculate_trip_fare([], new_route, req.pickup_node.id, req.dropoff_node.id)
                    
                    matches.append({
                        'request': CarpoolRequestSerializer(req).data,
                        'detour': detour,
                        'proposed_fare': fare
                    })
                    
        return Response(matches)

class CarpoolRequestViewSet(viewsets.ModelViewSet):
    queryset = CarpoolRequest.objects.all()
    serializer_class = CarpoolRequestSerializer

    def perform_create(self, serializer):
        serializer.save(passenger=self.request.user)

    @decorators.action(detail=True, methods=['get'])
    def offers(self, request, pk=None):
        carpool_req = self.get_object()
        offers = Offer.objects.filter(request=carpool_req)
        return Response(OfferSerializer(offers, many=True).data)

class OfferViewSet(viewsets.ModelViewSet):
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer

    def create(self, request, *args, **kwargs):
        # Driver offers to accept a request
        trip_id = request.data.get('trip')
        request_id = request.data.get('request')
        
        trip = get_object_or_404(Trip, id=trip_id, driver=request.user)
        carpool_req = get_object_or_404(CarpoolRequest, id=request_id)
        
        # Calculate detour and fare again for confirmation
        # (Usually you'd pass these from the matching_requests endpoint for consistency)
        curr_idx = trip.route.index(trip.current_node.id)
        remaining_route = trip.route[curr_idx:]
        new_route, detour = graph_service.calculate_best_detour(remaining_route, carpool_req.pickup_node.id, carpool_req.dropoff_node.id)
        
        if not new_route:
            return Response({'error': 'Cannot fulfill request'}, status=status.HTTP_400_BAD_REQUEST)
            
        fare = fare_service.calculate_trip_fare([], new_route, carpool_req.pickup_node.id, carpool_req.dropoff_node.id)
        
        offer = Offer.objects.create(
            trip=trip,
            request=carpool_req,
            detour=detour,
            fare=fare
        )
        return Response(OfferSerializer(offer).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        offer = self.get_object()
        if offer.request.passenger != request.user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        # Accept offer: update statuses and trip route
        offer.status = 'ACCEPTED'
        offer.save()
        
        carpool_req = offer.request
        carpool_req.status = 'ACCEPTED'
        carpool_req.save()
        
        # Update trip route
        trip = offer.trip
        curr_idx = trip.route.index(trip.current_node.id)
        remaining_route = trip.route[curr_idx:]
        new_route, _ = graph_service.calculate_best_detour(remaining_route, carpool_req.pickup_node.id, carpool_req.dropoff_node.id)
        
        trip.route = trip.route[:curr_idx] + new_route
        trip.save()
        
        return Response(OfferSerializer(offer).data)

    @decorators.action(detail=True, methods=['post'])
    def complete_trip(self, request, pk=None):
        trip = self.get_object()
        if trip.driver != request.user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        if trip.status == 'COMPLETED':
            return Response({'error': 'Trip already completed'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Complete trip and process payments
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            accepted_offers = Offer.objects.filter(trip=trip, status='ACCEPTED')
            driver_wallet = trip.driver.wallet
            
            for offer in accepted_offers:
                passenger_wallet = offer.request.passenger.wallet
                
                if passenger_wallet.balance < offer.fare:
                    return Response({'error': f'Passenger {offer.request.passenger.username} has insufficient balance.'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                # Transfer funds
                passenger_wallet.balance -= offer.fare
                passenger_wallet.save()
                
                driver_wallet.balance += offer.fare
                driver_wallet.save()
                
                # Record transactions
                Transaction.objects.create(
                    wallet=passenger_wallet, amount=-offer.fare, 
                    transaction_type='FARE_PAYMENT', trip=trip
                )
                Transaction.objects.create(
                    wallet=driver_wallet, amount=offer.fare, 
                    transaction_type='EARNING', trip=trip
                )
                
                # Mark request completed
                req = offer.request
                req.status = 'COMPLETED'
                req.save()
            
            trip.status = 'COMPLETED'
            trip.save()
            
        return Response(TripSerializer(trip).data)

class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @decorators.action(detail=False, methods=['post'])
    def top_up(self, request):
        amount = request.data.get('amount')
        try:
            amount = float(amount)
            if amount <= 0: raise ValueError()
        except (TypeError, ValueError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            
        wallet = self.request.user.wallet
        wallet.balance += Decimal(str(amount))
        wallet.save()
        
        Transaction.objects.create(
            wallet=wallet, amount=Decimal(str(amount)), 
            transaction_type='TOPUP'
        )
        
        return Response(WalletSerializer(wallet).data)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return self.queryset.filter(wallet__user=self.request.user)

# SSR Views
@login_required
def driver_dashboard(request):
    trips = Trip.objects.filter(driver=request.user)
    active_trips = trips.filter(status='ACTIVE')
    
    # Simple demo logic to show requests for the first active trip
    matches = []
    if active_trips.exists():
        trip = active_trips.first()
        try:
            curr_idx = trip.route.index(trip.current_node.id)
            remaining_route = trip.route[curr_idx:]
        except (ValueError, AttributeError):
            remaining_route = trip.route
            
        pending_requests = CarpoolRequest.objects.filter(status='PENDING')
        for req in pending_requests:
            if graph_service.is_within_radius(remaining_route, req.pickup_node.id) and \
               graph_service.is_within_radius(remaining_route, req.dropoff_node.id):
                
                new_route, detour = graph_service.calculate_best_detour(remaining_route, req.pickup_node.id, req.dropoff_node.id)
                if new_route:
                    fare = fare_service.calculate_trip_fare([], new_route, req.pickup_node.id, req.dropoff_node.id)
                    matches.append({
                        'request': req,
                        'detour': detour,
                        'fare': fare,
                        'trip_id': trip.id
                    })
                    
    context = {
        'trips': trips,
        'active_trips': active_trips,
        'matches': matches
    }
    return render(request, 'core/dashboard.html', context)
