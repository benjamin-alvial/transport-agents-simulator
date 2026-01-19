from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel

if __name__ == "__main__":
    sim = Kernel()

    # Create agents
    uber = Platform("uber")
    customer_sending = Customer("customer_sending", 10)
    customer_receiving = Customer("customer_receiving", 210)
    courier = Courier("courier", 0, 20, 30)

    sim.register_agent(uber)
    sim.register_agent(customer_sending)
    sim.register_agent(customer_receiving)
    sim.register_agent(courier)

    # Define already existing to-be-delivered parcels in the platform
    sample_parcel_1 = Parcel("socks", 100, 210, 0.5, 10)
    sample_parcel_2 = Parcel("books", 100, 210, 4, 10)
    sim.schedule(1.0, lambda _: uber.initialize_deliveries(
        parcels=[sample_parcel_1, sample_parcel_2],
    ), None)

    sim.schedule(5.0, lambda _: customer_sending.request_delivery(
        Parcel("laptop", 10, 100, 5, 10),
        uber
    ), None)

    sim.schedule(10.0, lambda _: courier.ask_for_parcels(uber), None)

    sim.schedule(15.0, lambda _: courier.start_delivery(), None)

    print("Starting simulation...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")