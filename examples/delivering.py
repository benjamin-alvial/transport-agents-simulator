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
                 action=customer_sending.send_delivery_request,
                 data={"parcel": Parcel("laptop", customer_sending.location, 100, 5, 10),
                       "platform": uber})

    sim.schedule(delay=5.0,
                 action=uber.register_courier,
                 data={"courier": courier})

    print("Starting simulation...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")