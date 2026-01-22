class Parcel:
    """
    A parcel that a Customer wants delivered.
    """

    def __init__(self, contents: str, origin_node_id: int, destination_node_id: int, weight: float, fare: float):
        self.contents: str = contents
        self.origin_node_id: int = origin_node_id
        self.destination_node_id: int = destination_node_id
        self.weight: float = weight
        self.fare: float = fare
        self.state: str = "WAITING_PICK_UP"

    def __repr__(self):
        return (
            f"Parcel(contents={self.contents}, origin={self.origin_node_id}, destination={self.destination_node_id}, weight={self.weight}, "
            f"fare={self.fare}, state={self.state})"
        )