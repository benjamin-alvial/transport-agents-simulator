from typing import List
from des import SimulationKernel, Agent, Message


# Example: Simple Auction Agents
class Auctioneer(Agent):
    """
    Example agent that runs an auction.
    """

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.current_auction = None
        self.bids = []

    def start_auction(self, item: str, starting_price: float, duration: float, bidders: List[str]):
        """Start a new auction"""
        self.current_auction = {
            'item': item,
            'starting_price': starting_price,
            'bidders': bidders
        }
        self.bids = []

        print(f"[t={self.sim.current_time:.1f}] Auctioneer: Starting auction for {item}")
        print(f"  Starting price: ${starting_price:.2f}, Duration: {duration}s")

        # Notify all bidders
        for bidder_id in bidders:
            self.send_message(bidder_id, 'auction_start', {
                'item': item,
                'starting_price': starting_price
            })

        # Schedule auction end
        self.schedule_action(duration, self.end_auction, None)

    def end_auction(self, data):
        """End the auction and announce winner"""
        print(f"\n[t={self.sim.current_time:.1f}] Auctioneer: Auction ended")

        if self.bids:
            # Find highest bid
            winner = max(self.bids, key=lambda b: b['amount'])
            print(f"  Winner: {winner['bidder_id']} with bid ${winner['amount']:.2f}")

            # Notify winner
            self.send_message(winner['bidder_id'], 'auction_won', {
                'item': self.current_auction['item'],
                'amount': winner['amount']
            })
        else:
            print("  No bids received")

        self.current_auction = None
        self.bids = []

    def receive_message(self, message: Message):
        """Handle incoming messages"""
        if message.msg_type == 'bid':
            bid_amount = message.content['amount']
            print(f"[t={self.sim.current_time:.1f}] Auctioneer: Received bid of ${bid_amount:.2f} from {message.sender_id}")
            self.bids.append({
                'bidder_id': message.sender_id,
                'amount': bid_amount,
                'time': self.sim.current_time
            })


class Bidder(Agent):
    """
    Example agent that participates in auctions.
    """

    def __init__(self, agent_id: str, max_bid: float, decision_delay: float = 1.0):
        super().__init__(agent_id)
        self.max_bid = max_bid
        self.decision_delay = decision_delay

    def receive_message(self, message: Message):
        """Handle incoming messages"""
        if message.msg_type == 'auction_start':
            item = message.content['item']
            starting_price = message.content['starting_price']

            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Received auction notification for {item}")

            # Schedule bid decision
            self.schedule_action(self.decision_delay, self.make_bid_decision, {
                'auctioneer': message.sender_id,
                'item': item,
                'starting_price': starting_price
            })

        elif message.msg_type == 'auction_won':
            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Won auction! Paid ${message.content['amount']:.2f}")

    def make_bid_decision(self, data):
        """Decide whether to bid and how much"""
        starting_price = data['starting_price']

        # Simple strategy: bid up to max_bid
        if starting_price <= self.max_bid:
            bid_amount = min(starting_price * 1.1, self.max_bid)
            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Deciding to bid ${bid_amount:.2f}")

            self.send_message(data['auctioneer'], 'bid', {
                'amount': bid_amount,
                'item': data['item']
            })
        else:
            print(f"[t={self.sim.current_time:.1f}] {self.agent_id}: Price too high, not bidding")


# Example usage
if __name__ == "__main__":
    sim = SimulationKernel()

    # Create agents
    auctioneer = Auctioneer("auctioneer_1")
    bidder1 = Bidder("bidder_alice", max_bid=100.0, decision_delay=0.5)
    bidder2 = Bidder("bidder_bob", max_bid=150.0, decision_delay=1.0)
    bidder3 = Bidder("bidder_carol", max_bid=80.0, decision_delay=0.8)

    # Register agents
    sim.register_agent(auctioneer)
    sim.register_agent(bidder1)
    sim.register_agent(bidder2)
    sim.register_agent(bidder3)

    # Start auction at time 1.0
    sim.schedule(1.0, lambda _: auctioneer.start_auction(
        item="Vintage Watch",
        starting_price=50.0,
        duration=5.0,
        bidders=["bidder_alice", "bidder_bob", "bidder_carol"]
    ), None)

    print("Starting simulation...\n")
    sim.run(until=20.0)
    print(f"\nSimulation complete. Final time: {sim.current_time:.1f}")


# Starting simulation...
#
# [t=1.0] Auctioneer: Starting auction for Vintage Watch
#   Starting price: $50.00, Duration: 5.0s
# [t=1.0] bidder_alice: Received auction notification for Vintage Watch
# [t=1.0] bidder_bob: Received auction notification for Vintage Watch
# [t=1.0] bidder_carol: Received auction notification for Vintage Watch
# [t=1.5] bidder_alice: Deciding to bid $55.00
# [t=1.5] Auctioneer: Received bid of $55.00 from bidder_alice
# [t=1.8] bidder_carol: Deciding to bid $55.00
# [t=1.8] Auctioneer: Received bid of $55.00 from bidder_carol
# [t=2.0] bidder_bob: Deciding to bid $55.00
# [t=2.0] Auctioneer: Received bid of $55.00 from bidder_bob
#
# [t=6.0] Auctioneer: Auction ended
#   Winner: bidder_alice with bid $55.00
# [t=6.0] bidder_alice: Won auction! Paid $55.00
#
# Simulation complete. Final time: 20.0