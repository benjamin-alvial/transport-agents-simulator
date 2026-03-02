from parcel_delivery_two.market import DeliveryRequest, Courier, Market
from parcel_delivery_two.environment import Network, matsim_io
from parcel_delivery_two.restrictions import ProhibitEdge
from parcel_delivery_two.routing import Router
from parcel_delivery_two.agents import Bus, CourierVehicle
from parcel_delivery_two.core import Kernel
from parcel_delivery_two.visualizers import MovementVisualizer

if __name__ == "__main__":

    # ================= MARKET =================


    # ================= NETWORK =================
    # Load MATSim network format into own Network class
    print("\nLoading network from MATSim xml file...")
    network = matsim_io.load_network_from_matsim("kelheim-v3.0-network-with-pt.xml")

    # MATSim should be run before executing this program
    print("\nCalculating and loading travel tiems...")
    matsim_io.load_historic_travel_times("kelheim-v3.1-25pct.5.events.xml.gz", network)

    # If we want to visualize a large network:
    print("\nCreating json for later visualization with Sigma...")
    network.export_for_sigma("kelheim.json")

    # ================= RESTRICTIONS =================


    # ================= ROUTING =================


    # ================= BUSES =================


    # ================= SIMULATION =================
