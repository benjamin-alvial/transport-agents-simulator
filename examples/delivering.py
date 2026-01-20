from parcel_delivery import Platform, Customer, Courier, Parcel, Kernel

if __name__ == "__main__":
    sim = Kernel()

    # Create agents
    platform = Platform("platform")
    customer_sending = Customer("customer_sending", 10)
    courier1 = Courier("courier1", 0, 20, 30)
    courier2 = Courier("courier2", 0, 20, 30)

    sim.register_agent(platform)
    sim.register_agent(customer_sending)
    sim.register_agent(courier1)
    sim.register_agent(courier2)

    sim.schedule(delay=5.0,
                 action=customer_sending.send_delivery_request,
                 data={"parcel": Parcel("laptop", customer_sending.location, 100, 5, 10),
                       "platform": platform})

    sim.schedule(delay=5.0,
                 action=platform.register_courier,
                 data={"courier": courier1})

    sim.schedule(delay=5.0,
                 action=platform.register_courier,
                 data={"courier": courier2})

    print("Starting simulation...\n")
    sim.run(until=100.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")