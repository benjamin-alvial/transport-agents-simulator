# Transport Agents Simulator

A discrete-event simulation framework for parcel delivery with couriers, a market, and traffic constraints over a road network.

## Overview

This simulator models a parcel delivery system where couriers with different vehicle types navigate a road network to deliver packages. It supports:

- **Multi-courier operations** with heterogeneous vehicle fleets
- **Centralized market** that assigns delivery requests to couriers
- **MATSim-compatible** road networks with historic travel times from 15-minute bins
- **Two VRP routing strategies**: fast heuristic (DEFAULT) or optimized Google OR-Tools (ORTOOLS)
- **Traffic restrictions** (prohibited edges, congestion pricing)
- **Business metrics** (fuel consumption, emissions, operational costs)
- **Interactive visualizations** of network congestion and vehicle movements for small networks

The general flow of the simulator is as follows: delivery requests and couriers are created by the user, the market assigns requests to couriers, each courier solves its own VRP with travel times given by a previous MATSim simulation and constraints defined by the user, metrics are calculated (distances traveled, delivered packages, emissions, etc.).

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/benjamin-alvial/transport-agents-simulator
cd transport-agents-simulator

# Install dependencies
pip install -r requirements.txt
```

### Run the Full Example

```bash
cd examples/full_example
python full_example.py
```

This will:
1. Load a sample road network from MATSim format
2. Assign 90 delivery requests to 4 couriers with different vehicles
3. Load historic travel times from MATSim events file and route vehicles with departure_time=8:00 AM
4. Apply congestion pricing and vehicle restrictions during routing
5. Run a 24-hour discrete-event simulation
6. Generate metrics CSVs and business analysis

### Run Tests

```bash
python -m pytest tests/ -v
```

## Basic Usage

First, it is expected that a MATSim simulation has been run and the following have been saved: 
- ``network.xml``: used to create the network 
- ``events.xml``: used to calculate historic travel times, by 15-minute bins, used during routing

```python
from parcel_delivery_two import MetricsCollector
from parcel_delivery_two.market import DeliveryRequest, Courier, Market
from parcel_delivery_two.environment import matsim_io
from parcel_delivery_two.agents import CourierVehicle
from parcel_delivery_two.core import Kernel

# Create delivery requests
requests = [DeliveryRequest(f"parcel_{i}", weight=10, origin=2, destination=3) 
            for i in range(10)]

# Create courier with vehicles
vehicles = [CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)]
courier = Courier("courier1", vehicles=vehicles, location=2)

# Assign requests to couriers
market = Market()
market.assign_delivery_requests(requests, [courier])

# Load network and historic travel times
network = matsim_io.load_network_from_matsim("input/network.xml")
matsim_io.load_historic_travel_times("input/events.xml", network)

# Route vehicles (departure_time required for historic travel times)
from parcel_delivery_two.routing import Router
router = Router(
    courier=courier,
    network=network,
    restrictions=[],
    departure_time=28800.0,  # 8:00 AM - required for time-dependent routing
    strategy="DEFAULT"       # or "ORTOOLS" for optimized routing
)
router.calculate_itinerary()

# Run simulation
sim = Kernel()
sim.set_network(network)
sim.register_courier(courier)
sim.run(until=86400)  # Run for 24 hours
```

## Key Features

### Market Assignment
- Round-robin assignment of delivery requests to couriers
- Capacity constraints per vehicle
- Location matching (couriers only take requests from their depot)

### Routing
Two VRP strategies available:

**DEFAULT Strategy** (fast, heuristic):
- Greedy capacity-fill assignment + nearest-neighbour stop ordering
- Dijkstra shortest-path routing
- Good for quick results and testing

**ORTOOLS Strategy** (optimized, slower):
- Google OR-Tools VRP solver for heterogeneous fleets
- Better solutions for large-scale problems

Both strategies use:
- **Time-dependent historic travel times** from 15-minute bins (requires departure_time)
- Vehicle-type specific restrictions (e.g., trucks can't use certain roads)
- Time-windowed restrictions (e.g., no trucks in city center 8-10am)
- Congestion pricing converted to time costs using Value of Travel Time (VTT)

### Simulation
- Discrete-event simulation with event queue
- Historic travel times loaded from MATSim events
- Per-vehicle tracking of distance, time, and costs

### Metrics & Analysis
- **Runtime metrics**: assignment rate, completion rate, average delivery time
- **Post-simulation business metrics**: fuel consumption, CO2 emissions, operational costs
- **Clean mode share**: percentage of deliveries by zero-emission vehicles

### Visualization
- Static network visualization (small networks)
- Dynamic congestion heatmaps with time sliders
- Vehicle movement animation with route tracing
- Sigma.js export for large network visualization

## Project Structure

```
transport-agents-simulator/
├── examples/
│   ├── full_example/           # Complete usage demo
│   ├── square_grid_example/    # 21x21 grid network
│   └── real_city_example/      # Real-world city (stub)
├── parcel_delivery_two/        # Main package
│   ├── agents/                 # TransportVehicle, CourierVehicle, Bus
│   ├── market/                 # DeliveryRequest, Courier, Market
│   ├── environment/            # Network, matsim_io, Node, Edge
│   ├── restrictions/           # ProhibitEdge, CongestionPricing
│   ├── routing/                # Router (VRP solver), ORToolsRouterStrategy
│   ├── core/                   # Kernel (DES engine)
│   ├── loggers/                # EdgeLogger, EventLogger
│   ├── metrics/                # MetricsCollector, PostSimulationMetrics
│   ├── visualizers/            # MovementVisualizer
│   └── utils/                  # time_utils
├── tests/                      # pytest test suite
└── BUSINESS_METRICS_FORMULAS.md # Detailed formulas documentation
```

## Examples

### Full Example
A simple toy network of 9 nodes

Complete demonstration with all features: congestion pricing, multiple couriers, business metrics.
The network is 

```bash
cd examples/full_example
python full_example.py
```

### Square Grid Example
Simple 21x21 grid network example:

```bash
cd examples/square_grid_example
python square_grid_example.py
```

### Real City Example
Simple 21x21 grid network example:

```bash
cd examples/square_grid_example
python square_grid_example.py
```

## Configuration

### Vehicle Types
Configure vehicle characteristics for business metrics:

```python
from parcel_delivery_two.metrics import VehicleTypeConfig

configs = {
    "car": VehicleTypeConfig(
        fuel_efficiency_km_per_l=15.0,      # ~6.7 L/100km
        fuel_price_per_liter=1.80,
        emission_factor_g_co2_per_l=2300,    # Gasoline
        is_clean_mode=False,
        labor_cost_per_hour=25.0
    ),
    "bike": VehicleTypeConfig(
        fuel_efficiency_km_per_l=float('inf'),  # No fuel
        fuel_price_per_liter=0.0,
        emission_factor_g_co2_per_l=0,
        is_clean_mode=True,
        labor_cost_per_hour=18.0
    ),
}
```

### Congestion Pricing
Add time-based tolls that affect routing decisions:

```python
from parcel_delivery_two.restrictions import CongestionPricing

# $5 toll for big trucks on edge 15 during morning rush
pricing = CongestionPricing(
    edge_id=15, 
    cost=5.0, 
    vehicle_type="bigtruck", 
    time_window=[28800, 36000]  # 8:00-10:00
)
```

## Output Files

After running a simulation, check the `output/` directory for:

- `edge_log.csv` - Edge entry/exit events
- `event_log.csv` - High-level simulation events  
- `metrics_per_vehicle.csv` - Distance, time, costs per vehicle
- `metrics_per_courier.csv` - Aggregated metrics per courier
- `metrics_totals.csv` - Overall simulation statistics
- `business_metrics.csv` - Post-simulation business analysis

## Documentation

- `CLAUDE.md` - Technical reference for LLM agents (complete API documentation)
- `BUSINESS_METRICS_FORMULAS.md` - Detailed formulas for business metrics calculations

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]
