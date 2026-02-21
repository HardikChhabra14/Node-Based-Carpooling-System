from decimal import Decimal

def calculate_passenger_fare(hops_occupancy, unit_price=10.0, base_fee=5.0):
    """
    Calculate fare for a passenger based on occupancy of hops they are in.
    hops_occupancy: List of integers representing number of passengers in each hop.
    """
    total_sum = sum(1.0 / n if n > 0 else 1.0 for n in hops_occupancy)
    fare = (Decimal(str(unit_price)) * Decimal(str(total_sum))) + Decimal(str(base_fee))
    return fare.quantize(Decimal('0.01'))

def calculate_trip_fare(current_occupancy_per_hop, route_nodes, pickup_node, dropoff_node, unit_price=10.0, base_fee=5.0):
    """
    Calculate the proposed fare for a new passenger.
    This requires knowing which hops in the route the passenger will be in.
    For Phase 1, we can simplify or use the specific formula.
    """
    # Find the range of indices in the route for the passenger
    try:
        start_idx = route_nodes.index(pickup_node)
        end_idx = route_nodes.index(dropoff_node)
    except ValueError:
        return Decimal('0.00')
    
    if start_idx >= end_idx:
        return Decimal('0.00')
    
    # Extract the occupancy for the hops the passenger is in.
    # A trip with nodes [A, B, C] has 2 hops: (A,B) and (B,C).
    # If pickup is A and dropoff is C, passenger is in both hops.
    # occupancy_per_hop should have length len(route_nodes) - 1.
    
    # For a new offer, we assume n_i will be (current_n_i + 1)
    relevant_occupancy = []
    for i in range(start_idx, end_idx):
        # If current_occupancy_per_hop is not provided, assume 1 (just the new passenger)
        current_n = current_occupancy_per_hop[i] if i < len(current_occupancy_per_hop) else 0
        relevant_occupancy.append(current_n + 1)
    
    return calculate_passenger_fare(relevant_occupancy, unit_price, base_fee)
