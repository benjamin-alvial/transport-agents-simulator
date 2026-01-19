from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel

if __name__ == "__main__":
    sim = Kernel()

    # Create agents
    uber = Platform("uber")
    customer_sending = Customer("customer_sending", 10)
    courier = Courier("courier", 0, 20, 30)

    sim.register_agent(uber)
    sim.register_agent(customer_sending)
    sim.register_agent(courier)

    sim.schedule(delay=5.0,
                 action=lambda _: customer_sending.send_delivery_request(_,_),
                 data=(Parcel("laptop", customer_sending.location, 100, 5, 10),uber))

    sim.schedule(delay=5.0,
                 action=lambda _: uber.register_courier(_),
                 data=courier)

    sim.schedule(10.0, lambda _: courier.ask_for_parcels(uber), None)

    sim.schedule(15.0, lambda _: courier.start_delivery(), None)

    print("Starting simulation...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")