import random
from parcel_delivery_two import MetricsCollector, ProhibitEdge
from parcel_delivery_two.market import DeliveryRequest, Courier, Market
from parcel_delivery_two.environment import matsim_io
from parcel_delivery_two.routing import Router
from parcel_delivery_two.agents import Bus, CourierVehicle
from parcel_delivery_two.core import Kernel
from parcel_delivery_two.metrics import PostSimulationMetrics, VehicleTypeConfig

if __name__ == "__main__":

    random.seed(123)


    metrics = MetricsCollector()

    # ================= NETWORK =================
    # Load MATSim network format into own Network class
    print("\nLoading network from MATSim xml file...")
    network = matsim_io.load_network_from_matsim("input/kelheim-v3.0-network-with-pt.xml")

    # Get all available node IDs for random sampling
    all_node_ids = list(network.nodes.keys())
    print(f"Network loaded with {len(all_node_ids)} nodes")

    # Sample 2 random depot locations
    depot_nodes = random.sample(all_node_ids, 2)
    depot_1, depot_2 = depot_nodes[0], depot_nodes[1]
    print(f"Selected depot locations: {depot_1}, {depot_2}")

    # MATSim should be run before executing this program
    print("\nCalculating and loading travel times...")
    matsim_io.load_historic_travel_times("input/kelheim-v3.1-25pct.5.events.xml.gz", network)

    # If we want to visualize a large network:
    print("\nCreating json for later visualization with Sigma...")
    network.export_for_sigma("kelheim.json")

    # ================= MARKET =================
    # Create ~100 random delivery requests
    # All deliveries originate from one of the depots
    num_deliveries = 100
    delivery_requests = []
    
    for i in range(num_deliveries):
        # Random origin from one of the two depots
        origin = random.choice(depot_nodes)
        # Random destination (different from origin)
        destination = random.choice([n for n in all_node_ids if n != origin])
        weight = random.uniform(5.0, 20.0)  # Random weight between 5-20
        delivery_requests.append(
            DeliveryRequest(f"parcel_{i}", weight=weight, origin=origin, destination=destination)
        )
    
    print(f"\nCreated {len(delivery_requests)} random delivery requests")

    # Create 5 couriers with mixed vehicle fleets
    couriers = []
    
    # Courier 1: 2 cars, based at depot_1
    cars_1 = [CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100) for _ in range(2)]
    courier_1 = Courier("courier1", vehicles=cars_1, location=depot_1)
    couriers.append(courier_1)
    
    # Courier 2: 3 bikes, based at depot_1
    bikes = [CourierVehicle(vehicle_type="bike", travel_time_factor=0.5, capacity=20) for _ in range(3)]
    courier_2 = Courier("courier2", vehicles=bikes, location=depot_1)
    couriers.append(courier_2)
    
    # Courier 3: 2 trucks, based at depot_2
    trucks = [CourierVehicle(vehicle_type="truck", travel_time_factor=1.5, capacity=150) for _ in range(2)]
    courier_3 = Courier("courier3", vehicles=trucks, location=depot_2)
    couriers.append(courier_3)
    
    # Courier 4: 1 car + 1 bike, based at depot_2
    mixed_4 = [
        CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100),
        CourierVehicle(vehicle_type="bike", travel_time_factor=0.5, capacity=20)
    ]
    courier_4 = Courier("courier4", vehicles=mixed_4, location=depot_2)
    couriers.append(courier_4)
    
    # Courier 5: 1 truck + 2 cars, based at depot_1
    mixed_5 = [
        CourierVehicle(vehicle_type="truck", travel_time_factor=1.5, capacity=150),
        CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100),
        CourierVehicle(vehicle_type="car", travel_time_factor=1.0, capacity=100)
    ]
    courier_5 = Courier("courier5", vehicles=mixed_5, location=depot_1)
    couriers.append(courier_5)
    
    print(f"Created {len(couriers)} couriers with {sum(len(c.vehicles) for c in couriers)} total vehicles")

    # Assign delivery requests to couriers
    market = Market()
    assigned, failed = market.assign_delivery_requests(
        delivery_requests=delivery_requests, 
        couriers=couriers, 
        strategy="DEFAULT"
    )
    metrics.record_delivery_assignment(assigned, len(delivery_requests))
    print(f"Assigned {assigned} requests, {failed} failed")

    # ================= RESTRICTIONS =================
    # Prohibit 100 random edges for all vehicles
    edge_ids = list(network.edges.keys())
    num_prohibited = min(100, len(edge_ids))
    prohibited_edges = random.sample(edge_ids, num_prohibited)
    restrictions = [ProhibitEdge(edge_id=eid) for eid in prohibited_edges]
    print(f"\nProhibited {len(restrictions)} edges for all vehicles")

    # ================= ROUTING =================
    # All vehicles depart at 8:00 (28800 seconds)
    departure_time = 28800.0
    routers = []
    
    for courier in couriers:
        router = Router(courier, network, restrictions, strategy="DEFAULT", departure_time=departure_time)
        routers.append(router)
    
    # Calculate itineraries for all couriers
    print("\nCalculating routes...")
    for router in routers:
        router.calculate_itinerary()
    print("Routing complete")

    # ================= BUSES =================
    # Add a bus with a simple route (using random edges)
    if len(network.edges) > 0:
        edge_ids = list(network.edges.keys())
        bus_route = random.sample(edge_ids, min(5, len(edge_ids)))
        bus = Bus("bus_kelheim", itinerary=bus_route, travel_time_factor=2.0)
        print(f"\nCreated bus with route: {bus_route}")
    else:
        bus = None
        print("\nNo edges available for bus route")

    # ================= SIMULATION =================
    sim = Kernel(metrics_collector=metrics)
    sim.initialize_loggers()
    sim.set_network(network)
    sim.set_restrictions(restrictions)

    # Register entities to simulation kernel
    for courier in couriers:
        sim.register_courier(courier)
    
    if bus:
        sim.register_entity(bus)

    # Schedule the couriers' departures at 8:00
    for courier in couriers:
        for vehicle in courier.vehicles:
            sim.schedule(delay=departure_time, action=vehicle.start_journey)

    # Schedule bus departure at 8:00
    if bus:
        sim.schedule(delay=departure_time, action=bus.start_journey)

    # Run simulation for 24 hours
    print("\nStarting simulation...")
    sim.run(until=86400)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")

    # ================= POST-SIMULATION METRICS =================
    # Define vehicle type configurations for cost and emission calculations
    vehicle_configs = {
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
        "truck": VehicleTypeConfig(
            fuel_efficiency_km_per_l=8.0,       # ~12.5 L/100km
            fuel_price_per_liter=1.80,
            emission_factor_g_co2_per_l=2600,    # Diesel
            is_clean_mode=False,
            labor_cost_per_hour=30.0
        ),
        "bus": VehicleTypeConfig(
            fuel_efficiency_km_per_l=4.0,       # ~25 L/100km
            fuel_price_per_liter=1.80,
            emission_factor_g_co2_per_l=2600,    # Diesel
            is_clean_mode=False,
            labor_cost_per_hour=40.0
        ),
    }

    # Print runtime metrics summary
    print("\n" + "="*50)
    print("SIMULATION METRICS SUMMARY")
    print("="*50)
    metrics.print_summary()

    # Create post-simulation analyzer and generate business metrics
    analyzer = PostSimulationMetrics.from_csvs("output/", vehicle_configs)
    analyzer.print_summary()
    analyzer.dump_to_csv("output/business_metrics.csv")
