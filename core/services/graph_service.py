from core.models import Node, Edge
from collections import deque

def get_shortest_path(start_node_id, end_node_id):
    """BFS to find the shortest path in the directed graph."""
    if start_node_id == end_node_id:
        return [start_node_id]
    
    queue = deque([[start_node_id]])
    visited = {start_node_id}
    
    while queue:
        path = queue.popleft()
        current_node_id = path[-1]
        
        edges = Edge.objects.filter(from_node_id=current_node_id)
        for edge in edges:
            if edge.to_node_id == end_node_id:
                return path + [edge.to_node_id]
            if edge.to_node_id not in visited:
                visited.add(edge.to_node_id)
                queue.append(path + [edge.to_node_id])
    return None

def get_distance(start_node_id, end_node_id, max_dist=None):
    """Get the shortest distance between two nodes."""
    if start_node_id == end_node_id:
        return 0
    
    queue = deque([(start_node_id, 0)])
    visited = {start_node_id}
    
    while queue:
        current_id, dist = queue.popleft()
        if max_dist is not None and dist >= max_dist:
            continue
            
        edges = Edge.objects.filter(from_node_id=current_id)
        for edge in edges:
            if edge.to_node_id == end_node_id:
                return dist + 1
            if edge.to_node_id not in visited:
                visited.add(edge.to_node_id)
                queue.append((edge.to_node_id, dist + 1))
    return float('inf')

def is_within_radius(route_node_ids, target_node_id, radius=2):
    """Check if target_node is within radius of any node in the route."""
    # This can be optimized by doing a multi-source BFS from all route nodes
    queue = deque([(node_id, 0) for node_id in route_node_ids])
    visited = set(route_node_ids)
    
    while queue:
        current_id, dist = queue.popleft()
        if current_id == target_node_id:
            return True
        if dist < radius:
            edges = Edge.objects.filter(from_node_id=current_id)
            for edge in edges:
                if edge.to_node_id not in visited:
                    visited.add(edge.to_node_id)
                    queue.append((edge.to_node_id, dist + 1))
    return False

def calculate_best_detour(remaining_route, pickup_id, dropoff_id):
    """
    Find the best way to insert pickup and dropoff into the remaining route.
    Returns (new_route, detour_length).
    Remaining route is a list of node IDs.
    """
    best_total_length = float('inf')
    best_route = None
    
    # Try all pairs of insertion points (i, j) where i <= j
    # Insertion points are indices in remaining_route where we diverge.
    # Case 1: Start -> ... -> r_i -> ... -> P -> ... -> D -> ... -> r_j -> ... -> End
    # Case 2: Start -> ... -> r_i -> ... -> P -> ... -> r_j -> ... -> r_k -> ... -> D -> ... -> r_l -> ... -> End
    # Actually, the simplest is to find path from r_i to P, then P to D, then D to r_j.
    # i can be from 0 to len(remaining_route)-1.
    # j can be from i to len(remaining_route)-1.
    
    # Precompute paths for efficiency if needed, but for now we search.
    
    n = len(remaining_route)
    original_length = n - 1
    
    for i in range(n):
        path_to_p = get_shortest_path(remaining_route[i], pickup_id)
        if path_to_p is None: continue
        
        path_p_to_d = get_shortest_path(pickup_id, dropoff_id)
        if path_p_to_d is None: continue
        
        for j in range(i, n):
            path_d_to_r_j = get_shortest_path(dropoff_id, remaining_route[j])
            if path_d_to_r_j is None: continue
            
            # Construct new route:
            # part1: remaining_route[0:i+1]
            # part2: path_to_p[1:]
            # part3: path_p_to_d[1:]
            # part4: path_d_to_r_j[1:]
            # part5: remaining_route[j+1:]
            
            # Note: handle cases where nodes might overlap (e.g. r_i == P)
            current_new_route = remaining_route[:i+1] + path_to_p[1:] + path_p_to_d[1:] + path_d_to_r_j[1:] + remaining_route[j+1:]
            
            # Remove consecutive duplicates just in case
            deduplicated_route = []
            if current_new_route:
                deduplicated_route.append(current_new_route[0])
                for k in range(1, len(current_new_route)):
                    if current_new_route[k] != current_new_route[k-1]:
                        deduplicated_route.append(current_new_route[k])
            
            # Check for no repeated nodes (requirement: "No node is repeated in a single trip")
            if len(deduplicated_route) == len(set(deduplicated_route)):
                total_length = len(deduplicated_route) - 1
                if total_length < best_total_length:
                    best_total_length = total_length
                    best_route = deduplicated_route
                    
    if best_route is None:
        return None, None
        
    detour = best_total_length - original_length
    return best_route, detour
