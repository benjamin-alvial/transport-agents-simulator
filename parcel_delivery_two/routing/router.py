import heapq
from typing import Dict, List, Optional, Tuple, Union

from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge
from parcel_delivery_two.restrictions.congestion_pricing import CongestionPricing
from parcel_delivery_two.routing.ortools_strategy import ORToolsRouterStrategy

# Type aliases for readability
_Adj = Dict[int, List[Tuple[int, int, float]]]          # node -> [(to, edge_id, cost)]
_CacheKey = Tuple[str, int]                              # (vehicle_type, source_node)


class Router:
    """Solves a VRP for a courier's fleet and writes itineraries to each vehicle.

    Both strategies use time-dependent routing based on historic travel times stored
    in 15-minute bins. The appropriate bin is selected based on ``departure_time``.

    The DEFAULT strategy uses a greedy capacity-fill for vehicle assignment and a
    nearest-neighbour heuristic for stop ordering. All routes depart from the
    courier's ``location`` (depot node). Shortest paths are computed via Dijkstra
    on historic travel times, with adjacency and path caches keyed by vehicle type
    so that ``ProhibitEdge`` restrictions are respected per vehicle.

    The ORTOOLS strategy uses Google OR-Tools to solve a Vehicle Routing Problem
    with time-dependent travel times. It supports heterogeneous fleets with
    vehicle-type-specific edge restrictions and capacities. Solve time is
    approximately 30 minutes per courier but can run longer for better solutions.

    Time-window restrictions are evaluated at departure_time to determine which
    edges are available during route planning.

    Congestion pricing costs are converted to time-equivalents using the courier's
    Value of Travel Time (VTT) and added to edge travel times for routing.

    Args:
        courier: The courier whose vehicles will be routed.
        network: The road network to route over.
        restrictions: Edge restrictions applied during routing (ProhibitEdge or
            CongestionPricing).
        departure_time: Time in seconds when vehicles depart. Required to select
            the appropriate 15-minute traffic bin for historic travel times.
        strategy: Routing strategy. ``"DEFAULT"`` uses greedy assignment and
            nearest-neighbour heuristic. ``"ORTOOLS"`` uses Google OR-Tools VRP
            solver with time-dependent routing.

    Raises:
        ValueError: If ``departure_time`` is None.
    """

    def __init__(
        self,
        courier: Courier,
        network: Network,
        restrictions: List[Union[ProhibitEdge, CongestionPricing]],
        departure_time: float,
        strategy: str = "DEFAULT",
    ):
        if departure_time is None:
            raise ValueError("departure_time is required for time-dependent routing")

        self.courier = courier
        self.network = network
        self.restrictions = restrictions
        self.strategy = strategy
        self.departure_time = departure_time
        self._adj: Dict[str, _Adj] = {}
        self._dist: Dict[_CacheKey, Dict[int, float]] = {}
        self._pred: Dict[_CacheKey, Dict[int, Optional[int]]] = {}

    def calculate_itinerary(self) -> None:
        """Solve the VRP and write an ``itinerary`` (ordered edge-ID list) to each vehicle.

        For the DEFAULT strategy:

        1. Assigns delivery requests greedily by capacity.
        2. Orders stops using a nearest-neighbour heuristic from the depot.
        3. Expands each hop into the shortest-path sequence of edge IDs,
           respecting any ``ProhibitEdge`` restrictions for the vehicle's type.

        For the ORTOOLS strategy, delegates to ORToolsRouterStrategy which:

        1. Builds time-dependent distance matrices for each vehicle type.
        2. Solves the VRP using Google OR-Tools with vehicle-specific transit callbacks.
        3. Assigns visits to vehicles and expands to edge itineraries.

        Raises:
            ValueError: If ``strategy`` is not ``"DEFAULT"`` or ``"ORTOOLS"``.
            ValueError: If the depot node is not present in the network.
            RuntimeError: If OR-Tools cannot find a feasible solution (ORTOOLS only).
        """
        if self.strategy == "ORTOOLS":
            # Delegate to OR-Tools strategy
            ortools_strategy = ORToolsRouterStrategy(
                self.courier,
                self.network,
                self.restrictions,
                self.departure_time,
            )
            ortools_strategy.calculate_itinerary()
            return

        if self.strategy != "DEFAULT":
            raise ValueError(f"Unknown routing strategy: {self.strategy!r}")

        depot = self.courier.location
        if depot not in self.network.nodes:
            raise ValueError(f"Depot node {depot} not found in network")

        vehicle_requests = self._assign_requests_to_vehicles()

        for vehicle, requests in zip(self.courier.vehicles, vehicle_requests):
            vehicle.assigned_requests = requests
            vehicle._destination_nodes = {r.destination for r in requests}
            vehicle.itinerary = self._build_vehicle_route(
                requests, vehicle.vehicle_type
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_adjacency(self, vehicle_type: str) -> _Adj:
        """Return (cached) adjacency for *vehicle_type*, filtered by restrictions.

        Travel times are determined by looking up historic travel times for the
        15-minute bin corresponding to departure_time. If no historic data is
        available for a bin, falls back to free-flow travel time.

        Args:
            vehicle_type: Vehicle type string used to filter prohibited edges
                and congestion pricing.

        Returns:
            Neighbor list mapping each node to reachable (to_node, edge_id, cost) tuples.
            Costs include historic travel time plus congestion pricing (converted to
            time using the courier's VTT).
        """
        if vehicle_type not in self._adj:
            # Separate prohibition and congestion pricing restrictions
            prohibited = set()
            congestion_costs: Dict[int, float] = {}

            for r in self.restrictions:
                if isinstance(r, ProhibitEdge):
                    if r.blocks(vehicle_type, self.departure_time):
                        prohibited.add(r.edge_id)
                elif isinstance(r, CongestionPricing):
                    cost = r.get_cost(vehicle_type, self.departure_time)
                    if cost > 0:
                        # Accumulate costs if multiple pricing rules apply to same edge
                        congestion_costs[r.edge_id] = (
                            congestion_costs.get(r.edge_id, 0.0) + cost
                        )

            adj: _Adj = {n: [] for n in self.network.nodes}
            vtt = self.courier.vtt

            # Calculate the 15-minute time bin for historic travel times
            time_bin = (int(self.departure_time) // 900) * 900

            for edge in self.network.edges.values():
                if edge.edge_id in prohibited:
                    continue

                # Use historic travel time if available, otherwise fall back to free-flow
                if time_bin in edge.travel_times:
                    travel_time = edge.travel_times[time_bin]
                else:
                    travel_time = edge.distance / edge.free_flow_speed

                # Add congestion pricing cost (converted to time using VTT)
                if edge.edge_id in congestion_costs and vtt > 0:
                    congestion_time = congestion_costs[edge.edge_id] / vtt
                    travel_time += congestion_time

                adj[edge.from_node].append((edge.to_node, edge.edge_id, travel_time))

            self._adj[vehicle_type] = adj
        return self._adj[vehicle_type]

    def _ensure_paths(self, vehicle_type: str, source: int) -> None:
        """Run Dijkstra from *source* for *vehicle_type* if not already cached."""
        key: _CacheKey = (vehicle_type, source)
        if key not in self._dist:
            dist, pred = self._dijkstra(vehicle_type, source)
            self._dist[key] = dist
            self._pred[key] = pred

    def _dijkstra(
        self, vehicle_type: str, source: int
    ) -> Tuple[Dict[int, float], Dict[int, Optional[int]]]:
        """Dijkstra's algorithm from *source* on the adjacency for *vehicle_type*.

        Args:
            vehicle_type: Determines which edges are available.
            source: Origin node ID.

        Returns:
            Tuple of (distances, predecessor_edge_ids). ``pred[v]`` is the edge
            ID used to reach node ``v`` on the shortest path from ``source``.
        """
        adj = self._get_adjacency(vehicle_type)
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

    def _path_edges(self, vehicle_type: str, source: int, target: int) -> List[int]:
        """Return the ordered edge-ID list for the shortest path from *source* to *target*.

        Returns an empty list when source == target or when target is unreachable.

        Args:
            vehicle_type: Determines which edges are available.
            source: Origin node ID.
            target: Destination node ID.

        Returns:
            List of edge IDs from source to target, in traversal order.
        """
        if source == target:
            return []
        self._ensure_paths(vehicle_type, source)
        pred = self._pred[(vehicle_type, source)]

        edges_reversed: List[int] = []
        node = target
        while node != source:
            edge_id = pred.get(node)
            if edge_id is None:
                return []  # target unreachable
            edges_reversed.append(edge_id)
            node = self.network.edges[edge_id].from_node

        return list(reversed(edges_reversed))

    def _nearest_idx(
        self, vehicle_type: str, source: int, destinations: List[int]
    ) -> int:
        """Return the index of the nearest destination from *source* for *vehicle_type*.

        Args:
            vehicle_type: Determines which edges are available.
            source: Current node.
            destinations: Candidate destination node IDs.

        Returns:
            Index into *destinations* of the closest node by shortest-path cost.
        """
        self._ensure_paths(vehicle_type, source)
        dist = self._dist[(vehicle_type, source)]
        return min(
            range(len(destinations)),
            key=lambda i: dist.get(destinations[i], float("inf")),
        )

    def _build_vehicle_route(
        self, requests: List[DeliveryRequest], vehicle_type: str
    ) -> List[int]:
        """Nearest-neighbour tour from the depot through all delivery destinations.

        Args:
            requests: Delivery requests assigned to one vehicle.
            vehicle_type: Used to respect edge restrictions.

        Returns:
            Ordered list of edge IDs covering the full route.
        """
        route: List[int] = []
        current = self.courier.location
        remaining = list(requests)

        while remaining:
            idx = self._nearest_idx(
                vehicle_type, current, [r.destination for r in remaining]
            )
            target = remaining[idx].destination
            route.extend(self._path_edges(vehicle_type, current, target))
            current = target
            remaining.pop(idx)

        return route

    def _assign_requests_to_vehicles(self) -> List[List[DeliveryRequest]]:
        """Greedily fill vehicles in order until each request is assigned.

        Returns:
            List of request lists, one per vehicle in ``courier.vehicles``.
        """
        loads = [0.0] * len(self.courier.vehicles)
        vehicle_requests: List[List[DeliveryRequest]] = [
            [] for _ in self.courier.vehicles
        ]

        for req in self.courier.assigned_delivery_requests:
            for i, vehicle in enumerate(self.courier.vehicles):
                if loads[i] + req.weight <= vehicle.capacity:
                    vehicle_requests[i].append(req)
                    loads[i] += req.weight
                    break

        return vehicle_requests
