"""ORTools-based VRP routing strategy with time-dependent travel times.

This module implements a Vehicle Routing Problem solver using Google OR-Tools,
supporting heterogeneous vehicle fleets with vehicle-type-specific restrictions
and time-dependent travel costs based on 15-minute traffic bins.
"""

import heapq
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.environment.edge import Edge
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing


# Type aliases
_Adj = Dict[int, List[Tuple[int, int, float]]]  # node -> [(to, edge_id, cost)]
_Location = int  # Node ID
_PathEdges = List[int]


@dataclass
class MatrixEntry:
    """Entry in the distance matrix containing travel time and path."""
    travel_time: float
    path_edges: _PathEdges


class ORToolsRouterStrategy:
    """VRP solver using Google OR-Tools with time-dependent routing.

    This strategy solves the Vehicle Routing Problem for a courier's heterogeneous
    fleet, respecting vehicle-type-specific edge restrictions and using travel
    times from historic 15-minute traffic bins.

    The solution process has three phases:
    1. Build per-vehicle-type distance matrices using time-dependent Dijkstra
    2. Solve VRP with OR-Tools using vehicle-specific transit callbacks
    3. Expand OR-Tools visit sequences into edge itineraries for the simulator

    Args:
        courier: The courier whose fleet will be routed.
        network: The road network to route over.
        restrictions: Edge restrictions (ProhibitEdge, CongestionPricing).
        departure_time: Time in seconds when vehicles depart. Determines which
            15-minute traffic bin to use for travel times.

    Raises:
        ValueError: If departure_time is None (required for time-dependent routing).
        RuntimeError: If OR-Tools cannot find a feasible solution.
    """

    def __init__(
        self,
        courier: Courier,
        network: Network,
        restrictions: List[Any],
        departure_time: Optional[float],
    ):
        if departure_time is None:
            raise ValueError(
                "ORToolsRouterStrategy requires departure_time for time-dependent routing. "
                "Use the DEFAULT strategy if you don't need time-dependent routing."
            )

        self.courier = courier
        self.network = network
        self.restrictions = restrictions
        self.departure_time = departure_time

        # Determine which 15-minute bin to use (0, 900, 1800, ..., 84600)
        self.time_bin = (int(departure_time) // 900) * 900

        # Get unique vehicle types in this courier's fleet
        self.vehicle_types = list(set(v.vehicle_type for v in courier.vehicles))

        # Distance matrices: vehicle_type -> from_idx -> to_idx -> MatrixEntry
        self.distance_matrices: Dict[str, Dict[int, Dict[int, MatrixEntry]]] = {}

        # Cache for Dijkstra computations
        self._adj_cache: Dict[str, _Adj] = {}

    def calculate_itinerary(self) -> None:
        """Solve the VRP and write itineraries to each vehicle.

        This method:
        1. Builds time-dependent distance matrices for each vehicle type
        2. Solves the VRP using OR-Tools
        3. Assigns visits to vehicles and expands to edge itineraries

        Raises:
            RuntimeError: If no feasible solution is found.
        """
        depot = self.courier.location
        if depot not in self.network.nodes:
            raise ValueError(f"Depot node {depot} not found in network")

        # Get all unique delivery destinations
        destinations = list(set(r.destination for r in self.courier.assigned_delivery_requests))
        if not destinations:
            # No deliveries to make - assign empty itineraries
            for vehicle in self.courier.vehicles:
                vehicle.assigned_requests = []
                vehicle._destination_nodes = set()
                vehicle.itinerary = []
            return

        # Build distance matrices for all vehicle types
        self._build_all_matrices(destinations)

        # Solve VRP with OR-Tools
        vehicle_routes = self._solve_vrp(destinations)

        # Assign routes to vehicles and expand to itineraries
        self._assign_and_expand(vehicle_routes, destinations)

    def _build_all_matrices(self, destinations: List[_Location]) -> None:
        """Build distance matrices for all vehicle types.

        Args:
            destinations: List of destination node IDs.
        """
        all_locations = [self.courier.location] + destinations

        for vehicle_type in self.vehicle_types:
            self.distance_matrices[vehicle_type] = self._build_matrix_for_type(
                vehicle_type, all_locations
            )

    def _build_matrix_for_type(
        self, vehicle_type: str, locations: List[_Location]
    ) -> Dict[int, Dict[int, MatrixEntry]]:
        """Build distance matrix for a specific vehicle type.

        For each pair of locations, runs Dijkstra to find the shortest path
        respecting vehicle-type-specific edge restrictions and using
        time-dependent travel costs.

        Args:
            vehicle_type: Type of vehicle (e.g., "car", "truck", "bike").
            locations: List of locations (depot + destinations).

        Returns:
            Matrix mapping from_idx -> to_idx -> MatrixEntry.
        """
        matrix: Dict[int, Dict[int, MatrixEntry]] = {}

        for from_loc in locations:
            matrix[from_loc] = {}

            # Run Dijkstra from this location
            distances, predecessors = self._dijkstra_for_type(vehicle_type, from_loc)

            for to_loc in locations:
                if from_loc == to_loc:
                    matrix[from_loc][to_loc] = MatrixEntry(0.0, [])
                else:
                    # Get path edges
                    path_edges = self._reconstruct_path(from_loc, to_loc, predecessors)
                    travel_time = distances.get(to_loc, float('inf'))

                    if travel_time == float('inf'):
                        # No path exists - use infinite cost
                        matrix[from_loc][to_loc] = MatrixEntry(float('inf'), [])
                    else:
                        matrix[from_loc][to_loc] = MatrixEntry(travel_time, path_edges)

        return matrix

    def _get_adjacency_for_type(self, vehicle_type: str) -> _Adj:
        """Get adjacency list for a vehicle type, filtered by restrictions.

        Args:
            vehicle_type: Vehicle type to filter for.

        Returns:
            Adjacency list with travel costs.
        """
        if vehicle_type in self._adj_cache:
            return self._adj_cache[vehicle_type]

        # Find prohibited edges for this vehicle type at departure time
        prohibited: Set[int] = set()
        congestion_costs: Dict[int, float] = {}

        for restriction in self.restrictions:
            if isinstance(restriction, ProhibitEdge):
                if restriction.blocks(vehicle_type, self.departure_time):
                    prohibited.add(restriction.edge_id)
            elif isinstance(restriction, CongestionPricing):
                cost = restriction.get_cost(vehicle_type, self.departure_time)
                if cost > 0:
                    congestion_costs[restriction.edge_id] = (
                        congestion_costs.get(restriction.edge_id, 0.0) + cost
                    )

        # Build adjacency list
        adj: _Adj = {n: [] for n in self.network.nodes}
        vtt = self.courier.vtt

        for edge in self.network.edges.values():
            if edge.edge_id in prohibited:
                continue

            # Get travel time from time bin if available, else free flow
            base_travel_time = edge.travel_times.get(
                self.time_bin,
                edge.distance / edge.free_flow_speed
            )

            # Add congestion pricing cost (converted to time)
            if edge.edge_id in congestion_costs and vtt > 0:
                congestion_time = congestion_costs[edge.edge_id] / vtt
                base_travel_time += congestion_time

            adj[edge.from_node].append((edge.to_node, edge.edge_id, base_travel_time))

        self._adj_cache[vehicle_type] = adj
        return adj

    def _dijkstra_for_type(
        self, vehicle_type: str, source: int
    ) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
        """Run Dijkstra from source for a specific vehicle type.

        Args:
            vehicle_type: Vehicle type for restrictions.
            source: Starting node ID.

        Returns:
            Tuple of (distances, predecessor_edges).
        """
        adj = self._get_adjacency_for_type(vehicle_type)

        dist: Dict[int, float] = {n: float("inf") for n in self.network.nodes}
        pred: Dict[int, Optional[int]] = {n: None for n in self.network.nodes}

        dist[source] = 0.0
        heap: List[Tuple[float, int]] = [(0.0, source)]

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for v, edge_id, cost in adj[u]:
                nd = d + cost
                if nd < dist[v]:
                    dist[v] = nd
                    pred[v] = edge_id
                    heapq.heappush(heap, (nd, v))

        return dist, pred

    def _reconstruct_path(
        self, source: int, target: int, predecessors: Dict[int, Optional[int]]
    ) -> _PathEdges:
        """Reconstruct path edges from Dijkstra predecessors.

        Args:
            source: Starting node.
            target: Destination node.
            predecessors: Mapping of node -> incoming edge ID.

        Returns:
            List of edge IDs from source to target.
        """
        if source == target:
            return []

        edges_reversed: List[int] = []
        node = target

        while node != source:
            edge_id = predecessors.get(node)
            if edge_id is None:
                return []  # No path exists
            edges_reversed.append(edge_id)
            # Get the from_node of this edge
            edge = self.network.edges[edge_id]
            node = edge.from_node

        return list(reversed(edges_reversed))

    def _solve_vrp(self, destinations: List[_Location]) -> Dict[int, List[int]]:
        """Solve the VRP using OR-Tools.

        Args:
            destinations: List of destination node IDs (not including depot).

        Returns:
            Mapping of vehicle_index -> list of visit indices (0 = depot).
        """
        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
        except ImportError:
            raise ImportError(
                "ortools is required for ORToolsRouterStrategy. "
                "Install with: pip install ortools>=9.8"
            )

        # Create mapping: index -> node_id
        # Index 0 is depot, 1..n are destinations
        index_to_node = {0: self.courier.location}
        node_to_index = {self.courier.location: 0}

        for i, dest in enumerate(destinations, start=1):
            index_to_node[i] = dest
            node_to_index[dest] = i

        num_locations = len(index_to_node)
        num_vehicles = len(self.courier.vehicles)

        # Create routing model
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        # Create transit callback that uses vehicle-type-specific matrices
        def transit_callback(from_index, to_index, vehicle_idx):
            """Return travel time between two locations for a specific vehicle."""
            from_node = index_to_node[manager.IndexToNode(from_index)]
            to_node = index_to_node[manager.IndexToNode(to_index)]

            vehicle = self.courier.vehicles[vehicle_idx]
            vehicle_type = vehicle.vehicle_type

            matrix = self.distance_matrices[vehicle_type]
            entry = matrix[from_node][to_node]

            # Convert infinite cost to a large number
            if entry.travel_time == float('inf'):
                return 1000000  # Large penalty
            return int(entry.travel_time * 1000)  # OR-Tools uses integers

        # Register the callback
        transit_callback_index = routing.RegisterTransitCallback(transit_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Add capacity constraints
        demands = [0]  # Depot has 0 demand
        for dest in destinations:
            # Find the request weight for this destination
            weight = 0.0
            for req in self.courier.assigned_delivery_requests:
                if req.destination == dest:
                    weight = req.weight
                    break
            demands.append(int(weight * 1000))  # Convert to integer

        def demand_callback(from_index):
            """Return demand at a location."""
            node = manager.IndexToNode(from_index)
            return demands[node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [int(v.capacity * 1000) for v in self.courier.vehicles],  # vehicle capacities
            True,  # start cumul to zero
            "Capacity",
        )

        # Search parameters - generous time limit given we can run for days
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 1800  # 30 minutes per courier
        search_parameters.log_search = False

        # Solve
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            raise RuntimeError(
                f"OR-Tools could not find a feasible solution for courier {self.courier.courier_id}. "
                f"This may be due to insufficient vehicle capacity or unreachable destinations."
            )

        # Extract routes
        vehicle_routes: Dict[int, List[int]] = {}
        for vehicle_idx in range(num_vehicles):
            vehicle_routes[vehicle_idx] = []
            index = routing.Start(vehicle_idx)

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                vehicle_routes[vehicle_idx].append(node_index)
                index = solution.Value(routing.NextVar(index))

        return vehicle_routes

    def _assign_and_expand(
        self, vehicle_routes: Dict[int, List[int]], destinations: List[_Location]
    ) -> None:
        """Assign requests to vehicles and expand routes to edge itineraries.

        Args:
            vehicle_routes: Mapping of vehicle_index -> list of visit indices.
            destinations: List of destination node IDs.
        """
        # Mapping: visit index -> destination node
        index_to_dest = {i + 1: dest for i, dest in enumerate(destinations)}

        for vehicle_idx, route_indices in vehicle_routes.items():
            vehicle = self.courier.vehicles[vehicle_idx]
            vehicle_type = vehicle.vehicle_type

            # Get requests for this vehicle's destinations
            assigned_requests: List[DeliveryRequest] = []
            destination_nodes: Set[int] = set()

            for idx in route_indices:
                if idx == 0:
                    continue  # Skip depot

                dest_node = index_to_dest[idx]
                destination_nodes.add(dest_node)

                # Find the request(s) for this destination
                for req in self.courier.assigned_delivery_requests:
                    if req.destination == dest_node:
                        assigned_requests.append(req)

            vehicle.assigned_requests = assigned_requests
            vehicle._destination_nodes = destination_nodes

            # Build itinerary from route
            itinerary: List[int] = []
            prev_node = self.courier.location

            for idx in route_indices[1:]:  # Skip depot at start
                dest_node = index_to_dest[idx]

                # Get pre-computed path edges
                matrix = self.distance_matrices[vehicle_type]
                entry = matrix[prev_node][dest_node]

                if entry.path_edges:
                    itinerary.extend(entry.path_edges)

                prev_node = dest_node

            vehicle.itinerary = itinerary
