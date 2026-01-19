class Parcel:
    """
    A parcel that can be delivered.
    """

    def __init__(self, contents: str, origin: int, destination: int, weight: float, fare: float):
        self.contents: str = contents
        self.origin: int = origin
        self.destination: int = destination
        self.weight: float = weight
        self.fare: float = fare
        self.state: str = "WAITING_PICK_UP"

    def __repr__(self):
        return (
            f"Parcel(contents={self.contents}, origin={self.origin}, destination={self.destination}, weight={self.weight}, "
            f"fare={self.fare}, state={self.state})"
        )