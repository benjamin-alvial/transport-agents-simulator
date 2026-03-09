from parcel_delivery_two import MetricsCollector
from parcel_delivery_two.market import DeliveryRequest, Courier, Market
from parcel_delivery_two.environment import Network, matsim_io
from parcel_delivery_two.restrictions import ProhibitEdge
from parcel_delivery_two.routing import Router
from parcel_delivery_two.agents import Bus, CourierVehicle
from parcel_delivery_two.core import Kernel
from parcel_delivery_two.visualizers import MovementVisualizer

if __name__ == "__main__":

    metrics = MetricsCollector()

    # ================= MARKET =================
    # 40 requests, each of contents of size 10.
    single_depot_node = 2
    single_destination_node = 3
    delivery_requests = [DeliveryRequest("parcel_"+str(i), weight=10, origin=single_depot_node, destination=single_destination_node) for i in range(40)]
    # 2 impossible requests that will not be assigned. Should trigger console warnings.
    delivery_requests.append(DeliveryRequest("parcel_impossible_by_location", weight=10, origin=10, destination=single_depot_node))
    delivery_requests.append(DeliveryRequest("parcel_impossible_by_capacity", weight=100000000, origin=single_depot_node, destination=single_depot_node))

    # Two couriers:
    # First with 3 cars of capacity 100 each (should get assigned 30 requests of size 10 each)
    cars = [CourierVehicle(vehicle_type="car", travel_time_factor=1, capacity=100) for _ in range(3)]
    courier_1 = Courier("courier1", vehicles=cars, location=single_depot_node)
    # Second with 5 bikes of capacity 20 each (should get assigned 10 requests of size 10 each)
    bikes = [CourierVehicle(vehicle_type="bike", travel_time_factor=0.5, capacity=20) for _ in range(5)]
    courier_2 = Courier("courier2", vehicles=bikes, location=single_depot_node)
    couriers = [courier_1, courier_2]

    # Assign the delivery requests to the couriers (couriers will update their state)
    market = Market()
    assigned, failed = market.assign_delivery_requests(delivery_requests=delivery_requests, couriers=couriers, strategy="DEFAULT")
    metrics.record_delivery_assignment(assigned, len(delivery_requests))

    # ================= NETWORK =================
    # Load MATSim network format into own Network class
    network = matsim_io.load_network_from_matsim("input/network.xml")
    print("\nGenerating visualization for network...")
    network.visualize() # Works for small networks

    # MATSim should be run before executing this program
    matsim_io.load_historic_travel_times("input/events.xml", network)
    print("\nGenerating visualization for congested network through the day...")
    network.visualize_dynamic_congestion() # Works for small networks
    network.export_for_sigma("output/network.json")  # Prefer this option for large networks

    # ================= RESTRICTIONS =================
    # Prohibit edge 5: 2->6 for all
    prohibit_edge_all_middle = ProhibitEdge(edge_id=5)
    # Prohibit edge 15: 2->7 and edge 19: 2->5 for cars only
    prohibit_edge_car_bottom = ProhibitEdge(edge_id=15, vehicle_type="car")
    prohibit_edge_car_top = ProhibitEdge(edge_id=19, vehicle_type="car")
    restrictions = [prohibit_edge_all_middle, prohibit_edge_car_bottom, prohibit_edge_car_top]

    # ================= ROUTING =================
    router_1 = Router(courier_1, network, restrictions, strategy="DEFAULT")
    router_2 = Router(courier_2, network, restrictions, strategy="DEFAULT")
    routers = [router_1, router_2]
    for router in routers:
        # Calculates shortest path through all deliveries and updates courier's state
        router.calculate_itinerary()

    # ================= BUSES =================
    bus_263 = Bus("bus_263", itinerary=[5, 7], travel_time_factor=2)

    # ================= SIMULATION =================
    sim = Kernel(metrics_collector=metrics)
    sim.initialize_loggers()
    sim.set_network(network)

    # Register entities to simulation kernel
    for courier in couriers:
        sim.register_courier(courier)
    sim.register_entity(bus_263)

    # Schedule the couriers' departures at 8:00
    for courier in couriers:
        for vehicle in courier.vehicles:
            sim.schedule(delay=28800.0,
                         action=vehicle.start_journey)

    # Schedule a bus departure at 8:00
    sim.schedule(delay=28800.0,
                 action=bus_263.start_journey)

    # Run simulation for the 24 hours of the day
    print("Starting simulation...\n")
    sim.run(until=86400)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")
    vis = MovementVisualizer(network)
    vis.visualize()