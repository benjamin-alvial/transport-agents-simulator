import random

from parcel_delivery_two.market import DeliveryRequest, Courier, Market
from parcel_delivery_two.environment import matsim_io
from parcel_delivery_two.routing import Router
from parcel_delivery_two.agents import CourierVehicle
from parcel_delivery_two.core import Kernel
from parcel_delivery_two.visualizers import MovementVisualizer

if __name__ == "__main__":

    # ================= MARKET =================
    # 40 requests, each of contents of size 10.
    single_depot_node = 220
    random.seed(42)
    delivery_requests = [
        DeliveryRequest(
            "parcel_" + str(i),
            weight=10,
            origin=single_depot_node,
            destination=random.randint(0, 420)
        )
        for i in range(40)]

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
    market.assign_delivery_requests(delivery_requests=delivery_requests, couriers=couriers, strategy="DEFAULT")

    # ================= NETWORK =================
    # Load MATSim network format into own Network class
    network = matsim_io.load_network_from_matsim("input/square_grid_21x21_network.xml")
    print("\nGenerating visualization for network...")
    # network.visualize() # Works for small networks

    # MATSim should be run before executing this program
    matsim_io.load_historic_travel_times("input/3.events.xml.gz", network)
    print("\nGenerating visualization for congested network through the day...")
    # network.visualize_dynamic_congestion()  # Works for small networks
    # network.export_for_sigma("output/grid.json")  # Prefer this option for large networks

    # ================= RESTRICTIONS =================
    restrictions = []

    # ================= ROUTING =================
    departure_time = 28800.0
    router_1 = Router(courier_1, network, restrictions, strategy="DEFAULT", departure_time=departure_time)
    router_2 = Router(courier_2, network, restrictions, strategy="DEFAULT", departure_time=departure_time)
    routers = [router_1, router_2]
    for router in routers:
        # Calculates shortest path through all deliveries and updates courier's state
        router.calculate_itinerary()

    # ================= SIMULATION =================
    sim = Kernel()
    sim.initialize_loggers()
    sim.set_network(network)

    # Register entities to simulation kernel
    for courier in couriers:
        sim.register_courier(courier)

    # Schedule the couriers' departures at 8:00
    for courier in couriers:
        for vehicle in courier.vehicles:
            sim.schedule(delay=28800.0,
                         action=vehicle.start_journey)

    # Run simulation for the 24 hours of the day
    print("Starting simulation...\n")
    sim.run(until=86400)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")
    vis = MovementVisualizer(network)
    vis.visualize(show_routes=True)