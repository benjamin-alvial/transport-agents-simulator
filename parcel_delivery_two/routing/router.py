import heapq
from typing import Dict, List, Optional, Tuple

from parcel_delivery_two.market.courier import Courier
from parcel_delivery_two.market.delivery_request import DeliveryRequest
from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.restrictions.prohibit_edge import ProhibitEdge

# Type aliases for readability
_Adj = Dict[int, List[Tuple[int, int, float]]]          # node -> [(to, edge_id, cost)]
_CacheKey = Tuple[str, int]                              # (vehicle_type, source_node)


class Router:
    """Solves a VRP for a courier's fleet and writes itineraries to each vehicle.

    The DEFAULT strategy uses a greedy capacity-fill for vehicle assignment and a
    nearest-neighbour heuristic for stop ordering. All routes depart from the
    courier's ``location`` (depot node). Shortest paths are computed via Dijkstra
    on free-flow travel times, with adjacency and path caches keyed by vehicle type
    so that ``ProhibitEdge`` restrictions are respected per vehicle.

    Args:
        courier: The courier whose vehicles will be routed.
        network: The road network to route over.
        restrictions: Edge/vehicle-type prohibitions applied during routing.
        strategy: Routing strategy. Only ``"DEFAULT"`` is currently supported.
    """

    def __init__(
        self,
        courier: Courier,
        network: Network,
        restrictions: List[ProhibitEdge],
        strategy: str = "DEFAULT",
    ):
        self.courier = courier
        self.network = network
        self.restrictions = restrictions
        self.strategy = strategy
        self._adj: Dict[str, _Adj] = {}
        self._dist: Dict[_CacheKey, Dict[int, float]] = {}
        self._pred: Dict[_CacheKey, Dict[int, Optional[int]]] = {}

    def calculate_itinerary(self) -> None:
        """Solve the VRP and write an ``itinerary`` (ordered edge-ID list) to each vehicle.

        For each vehicle in the courier's fleet the method:

        1. Assigns delivery requests greedily by capacity.
        2. Orders stops using a nearest-neighbour heuristic from the depot.
        3. Expands each hop into the shortest-path sequence of edge IDs,
           respecting any ``ProhibitEdge`` restrictions for the vehicle's type.

        Raises:
            ValueError: If ``strategy`` is not ``"DEFAULT"``.
            ValueError: If the depot node is not present in the network.
        """
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

        Args:
            vehicle_type: Vehicle type string used to filter prohibited edges.

        Returns:
            Neighbor list mapping each node to reachable (to_node, edge_id, cost) tuples.
        """
        if vehicle_type not in self._adj:
            prohibited = {
                r.edge_id
                for r in self.restrictions
                if r.blocks(vehicle_type)
            }
            adj: _Adj = {n: [] for n in self.network.nodes}
            for edge in self.network.edges.values():
                if edge.edge_id in prohibited:
                    continue
                cost = edge.distance / edge.free_flow_speed
                adj[edge.from_node].append((edge.to_node, edge.edge_id, cost))
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
