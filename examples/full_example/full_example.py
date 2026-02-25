from parcel_delivery_two.market import DeliveryRequest, Vehicle, Courier, Market
from parcel_delivery_two.environment import Network, matsim_io
from parcel_delivery_two.restrictions import ProhibitEdge
from parcel_delivery_two.routing import Router
from parcel_delivery_two.agents import Bus
from parcel_delivery_two.core import Kernel

if __name__ == "__main__":

    # ================= MARKET =================
    # 40 requests, each of contents of size 10.
    destination_node = 3
    delivery_requests = [DeliveryRequest("parcel_"+str(i), weight=10, destination=destination_node) for i in range(40)]

    # Two couriers:
    # First with 3 cars of capacity 100 each (should get assigned 30 requests of size 10 each)
    cars = [Vehicle(vehicle_type="car", travel_time_factor=1, capacity=100) for _ in range(3)]
    courier_1 = Courier("courier_1", vehicles=cars)
    # Second with 5 bikes of capacity 20 each (should get assigned 10 requests of size 10 each)
    bikes = [Vehicle(vehicle_type="bike", travel_time_factor=0.5, capacity=20) for _ in range(5)]
    courier_2 = Courier("courier_2", vehicles=bikes)
    couriers = [courier_1, courier_2]

    # Assign the delivery requests to the couriers (couriers will update their state)
    market = Market()
    market.assign_delivery_requests(delivery_requests=delivery_requests, couriers=couriers, strategy="DEFAULT")

    # ================= NETWORK =================
    # Load MATSim network format into own Network class
    network = matsim_io.load_network_from_matsim("network.xml")
    print("\nGenerating visualization for network...")
    network.visualize()

    # MATSim should be run here, or before executing this program
    matsim_io.load_historic_travel_times("events.xml", network)
    print("\nGenerating visualization for shortest path on congested network...")
    network.visualize_dynamic_congestion()

    # ================= RESTRICTIONS =================
    # Prohibit edge 5: 2->6 for all
    prohibit_edge_all = ProhibitEdge(edge_id=5)
    # Prohibit edge 15: 2->7 for cars only
    prohibit_edge_car = ProhibitEdge(edge_id=5, vehicle_type="car")
    restrictions = [prohibit_edge_car, prohibit_edge_car]

    # ================= ROUTING =================
    router_1 = Router(courier_1, network, restrictions, strategy="DEFAULT")
    router_2 = Router(courier_1, network, restrictions, strategy="DEFAULT")
    routers = [router_1, router_2]
    for router in routers:
        # Calculates shortest path through all deliveries and updates courier's state
        router.calculate_itinerary()

    # ================= BUSES =================
    bus_263 = Bus("bus_263", [2, 6, 3])

    # ================= SIMULATION =================
    sim = Kernel()
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