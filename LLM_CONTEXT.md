# LLM Context: Transport Agents Simulator

> **AI Assistant Development Note:** This codebase was developed with the assistance of Claude Code (Opus 4) and is now maintained with OpenCode (Kimi k2.5). This document serves as the canonical reference for AI assistants working on this project.

A discrete-event simulation framework for parcel delivery with multiple couriers, road networks, and traffic constraints.

## How to orient yourself at session start

1. Read this file top to bottom — it is kept current.
2. Check the **Status** section to see what is done and what is next.
3. The canonical usage script is `examples/full_example/full_example.py` — all API decisions flow from it.
4. Run `python -m pytest tests/ -v` to confirm the current baseline is green before touching anything.
5. Install dependencies with `pip install -r requirements.txt` if you haven't already.

## Project Layout

```
transport-agents-simulator/
├── examples/
│   ├── full_example/full_example.py        # Complete usage with all features
│   ├── square_grid_example/square_grid_example.py  # 21x21 grid network example
│   └── real_city_example/real_city_example.py      # Real-world network
├── parcel_delivery_two/                    # active package
│   ├── agents/           - TransportVehicle, CourierVehicle, Bus
│   ├── market/           - DeliveryRequest, Courier, Market
│   ├── environment/     - Network, matsim_io, Node, Edge
│   ├── restrictions/    - ProhibitEdge, CongestionPricing
│   ├── routing/         - Router, ORToolsRouterStrategy
│   ├── core/            - Kernel
│   ├── loggers/         - BaseLogger, EdgeLogger, EventLogger
│   ├── utils/           - time_utils (format_time)
│   ├── visualizers/     - MovementVisualizer
│   └── metrics/         - MetricsCollector, VehicleMetrics, PostSimulationMetrics, VehicleTypeConfig
├── tests/
│   ├── test_agents.py
│   ├── test_market.py
│   ├── test_routing.py
│   ├── test_routing_ortools.py  # OR-Tools routing strategy tests
│   ├── test_environment.py
│   └── test_restrictions.py
├── BUSINESS_METRICS_FORMULAS.md            # Formulas for post-simulation business metrics
└── parcel_delivery/    (old package — git history only, do not use)
```

## Conventions

- **One class per file.** File name matches class name in snake_case.
- **Docstrings on every public class and method** (Google-style: Args / Raises / Returns).
- **Tests live in `tests/test_<module>.py`**, grouped by class using pytest classes.
- **Stubs use `pass`** — add behavior only when explicitly asked.
- **Errors are custom exceptions** defined in the same file as the raising class and exported from the package `__init__.py`.
- Do not touch `parcel_delivery/` — it exists in git history only.

## Key Classes & Signatures

```python
# agents/
TransportVehicle(entity_id: str, travel_time_factor: float = 1.0, itinerary: List[int] = None)
  .entity_id: str
  .travel_time_factor: float
  .itinerary: List[int]                     # edge IDs to traverse
  .start_journey()                          # begins DES traversal

CourierVehicle(vehicle_type: str, travel_time_factor: float, capacity: int)
  .vehicle_type: str
  .capacity: int
  .itinerary: List[int]                     # set by Router
  .assigned_requests: List[DeliveryRequest] # set by Router
  ._destination_nodes: Set[int]              # set by Router
  .start_journey()                          # records start_time on requests
  # inherits from TransportVehicle

Bus(entity_id: str, itinerary: List[int], travel_time_factor: float = 2.0)
  # inherits from TransportVehicle

# market/
DeliveryRequest(name: str, weight: float, origin: int, destination: int)
  .start_time: float                        # set when vehicle starts journey
  .completion_time: float                   # set when parcel delivered
  .get_delivery_time() -> float             # delivery duration in seconds
Courier(courier_id: str, vehicles: List[CourierVehicle], location: int, vtt: float = 30.0/3600)
  .location: int                            # depot node
  .vtt: float                               # Value of Travel Time ($/second, default $30/hr = 0.00833$/s)
  .assigned_delivery_requests: List[DeliveryRequest]   # set by Market
  .total_capacity() -> float
  .remaining_capacity() -> float
Market().assign_delivery_requests(delivery_requests, couriers, strategy="DEFAULT") -> Tuple[int, int]
  # Returns (assigned_count, failed_count)
  # Logs warnings for LocationMismatchError and ExcessDemandError instead of raising

# metrics/
MetricsCollector()                          # Singleton - runtime metrics
  .record_edge_completion(entity_id, distance, travel_time, monetary_cost: float = 0.0)
  .record_delivery_assignment(assigned: int, total: int)
  .record_delivery_completion(vehicle_id, courier_id, delivery_time)
  .get_delivery_assignment_rate() -> float  # assigned / total requests
  .get_delivery_completion_rate() -> float  # delivered / assigned
  .get_average_delivery_time() -> float     # avg time from start to delivery
  .get_total_monetary_cost() -> float       # total congestion pricing costs across all vehicles
  .get_total_distance() -> float            # total distance across all vehicles
  .get_total_travel_time() -> float         # total travel time across all vehicles
  .get_vehicle_metrics(entity_id) -> VehicleMetrics  # metrics for specific vehicle
  .get_all_vehicle_metrics() -> Dict[str, VehicleMetrics]  # all vehicle metrics
  .get_summary() -> Dict[str, Any]          # complete summary with totals and breakdowns
  .print_summary()                          # pretty print to console
  .dump_to_csv()                            # Writes per-vehicle, per-courier, and totals CSVs
  .reset()                                  # clear all collected metrics

VehicleMetrics                              # Per-vehicle/courier metrics dataclass
  .distance_traveled: float
  .travel_time: float
  .monetary_cost: float
  .edges_traversed: int
  .delivery_times: List[float]
  .get_average_delivery_time() -> float

PostSimulationMetrics.from_csvs(output_dir, vehicle_configs)  # Business metrics analyzer
  # Reads simulation CSVs and calculates operational costs, emissions, mode share
  .total_fuel_consumption_l() -> float
  .total_emissions_kg_co2() -> float
  .total_operational_cost() -> float        # fuel + labor + congestion
  .cost_per_delivery() -> float
  .clean_mode_share() -> float              # clean deliveries / total deliveries
  .fleet_fuel_efficiency_km_per_l() -> float
  .fleet_emission_factor_g_per_km() -> float
  .print_summary()                           # Pretty print with emojis
  .dump_to_csv(filepath)                     # Write business_metrics.csv

VehicleTypeConfig(
  fuel_efficiency_km_per_l: float,          # km per liter (inf for zero-emission)
  fuel_price_per_liter: float,              # $/L
  emission_factor_g_co2_per_l: float,       # g CO2/L (gasoline ~2300, diesel ~2600)
  is_clean_mode: bool,                      # counts toward clean mode share
  labor_cost_per_hour: float                # $/hour driver wage
)

# environment/
Network().visualize()
Network().visualize_dynamic_congestion()
Network().export_for_sigma(filepath: str)              # Export to JSON for Sigma.js visualization
matsim_io.load_network_from_matsim(filepath: str) -> Network
matsim_io.load_historic_travel_times(filepath: str, network: Network)

# restrictions/
ProhibitEdge(edge_id: int, vehicle_type: str = None, time_window: List[float] = None)   # None = all vehicle types, time_window=[start, end] in seconds
CongestionPricing(edge_id: int, cost: float, vehicle_type: str = None, time_window: List[float] = None)   # cost in dollars; converted to time using courier.vtt for routing

# routing/
Router(courier, network, restrictions, departure_time: float, strategy="DEFAULT").calculate_itinerary()
  # uses courier.location as depot; departure_time required for historic travel times
  # strategies: "DEFAULT" (greedy+nearest-neighbour), "ORTOOLS" (Google OR-Tools VRP)
  # both strategies use time-dependent historic travel times from 15-minute bins

ORToolsRouterStrategy(courier, network, restrictions, departure_time).calculate_itinerary()
  # Google OR-Tools VRP solver for heterogeneous fleets with vehicle-type-specific restrictions
  # ~30 minute solve time per courier, supports 1000+ deliveries across 50+ vehicles

# visualizers/
MovementVisualizer(network)                # Visualizes entity movements using EdgeLogger data
  .animate(n_frames=300, interval_ms=50, show_routes=False)   # Auto-playing animation
  .visualize(n_steps=300, show_routes=False)                  # Interactive slider view

# utils/
format_time(time_in_seconds: float) -> str  # Format seconds as "XhYmZs"

# core/
Kernel()
  .current_time: float
  .initialize_loggers()
  .set_network(network)
  .set_restrictions(restrictions)           # required for congestion pricing cost tracking during simulation
  .register_courier(courier)                # injects _kernel, sets entity_id
  .register_entity(entity)
  .schedule(delay: float, action: Callable)
  .run(until: float)
```

## Design Decisions

| Decision                                    | Rationale |
|---------------------------------------------|---|
| Round-robin assignment (DEFAULT strategy)   | Fair distribution; respects each courier's total fleet capacity |
| Location mismatch logs warning              | Log and continue for operational visibility without stopping simulation |
| Excess demand logs warning                  | Log and continue for capacity overflows; return counts from Market |
| `remaining_capacity` on Courier, not Market | Capacity is a courier property; Market only orchestrates |
| Unified TransportVehicle base class         | DRY: Bus and CourierVehicle share travel logic |
| Explicit vehicle request assignment         | Router stores `assigned_requests` on vehicles for delivery tracking |

## Status

- [x] Skeleton classes — all modules in `parcel_delivery_two/`
- [x] Market — round-robin assignment, `ExcessDemandError`, `LocationMismatchError`, origin matching, docstrings
- [x] Environment — Node, Edge, Network (add_node/add_edge, KeyError on unknown refs, static visualize); matsim_io.load_network_from_matsim (parses nodes/links from MATSim XML)
- [x] Restrictions — ProhibitEdge(edge_id, vehicle_type=None, time_window=None); CongestionPricing(edge_id, cost, vehicle_type=None, time_window=None) with VTT-based cost conversion; Router respects restrictions at departure_time
- [x] Routing — Two VRP strategies: (1) DEFAULT: greedy vehicle fill + nearest-neighbour stops; (2) ORTOOLS: Google OR-Tools VRP solver for heterogeneous fleets. Both use time-dependent historic travel times from 15-minute bins; Dijkstra shortest paths with vehicle-type restrictions; sets vehicle.itinerary (List[int] of edge IDs); uses courier.location as depot
- [x] Agents — TransportVehicle base class with DES travel; CourierVehicle for couriers (capacity, vehicle_type); Bus with fixed travel_time_factor=2.0; both use itinerary (edge IDs)
- [x] Core — Kernel DES engine (event queue, scheduling, entity registry); injects `_kernel` into vehicles on `register_courier`; sets `entity_id`; dumps loggers at end of `run()`
- [x] Loggers — BaseLogger (singleton-per-subclass, CSV dump), EdgeLogger (`edge_log.csv`), EventLogger (`event_log.csv`); `utils/time_utils.format_time`
- [x] Visualizers — MovementVisualizer(network); `.animate()` reads EdgeLogger entries, interpolates positions, FuncAnimation
- [x] Metrics — MetricsCollector tracks assignment rate, completion rate, average delivery time, and total monetary cost (congestion pricing) per vehicle, per courier, and overall; PostSimulationMetrics calculates business metrics (fuel consumption, emissions, operational costs, clean mode share) from simulation CSVs
