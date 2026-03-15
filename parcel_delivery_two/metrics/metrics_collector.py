"""Metrics collection for simulation tracking."""

import csv
import os
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class VehicleMetrics:
    """Metrics for a single vehicle."""
    distance_traveled: float = 0.0
    travel_time: float = 0.0
    edges_traversed: int = 0
    monetary_cost: float = 0.0
    delivery_times: list = None

    def __post_init__(self):
        if self.delivery_times is None:
            self.delivery_times = []

    def get_average_delivery_time(self) -> float:
        """Get average delivery time for this vehicle/courier."""
        if not self.delivery_times:
            return 0.0
        return sum(self.delivery_times) / len(self.delivery_times)


class MetricsCollector:
    """Collects and aggregates simulation metrics.
    
    Tracks per-vehicle and aggregate metrics for distance traveled
    and travel time. Metrics can be saved to CSV and printed at the
    end of a simulation.
    
    Example:
        kernel = MetricsCollector()  # Singleton
        # During simulation, vehicles report edge completions
        kernel.record_edge_completion("bus_1", distance=1000, travel_time=60)
        
        # After simulation
        kernel.dump_to_csv()  # Saves to output/metrics.csv
        kernel.print_summary()  # Pretty prints to console
    """
    
    _instance = None
    vehicles_filename = "metrics_per_vehicle.csv"
    couriers_filename = "metrics_per_courier.csv"
    totals_filename = "metrics_totals.csv"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._vehicle_metrics: Dict[str, VehicleMetrics] = {}
        self._courier_metrics: Dict[str, VehicleMetrics] = {}
        self._total_distance = 0.0
        self._total_travel_time = 0.0
        self._total_monetary_cost = 0.0
        self._delivery_requests_total = 0
        self._delivery_requests_assigned = 0
        self._delivery_requests_delivered = 0
    
    def _get_courier_id(self, entity_id: str) -> str:
        """Extract courier ID from vehicle entity ID.
        
        Courier vehicles have format: "{courier_id}_{vehicle_type}_{index}"
        Buses have format like: "bus_1" (no courier)
        
        Returns:
            Courier ID if this is a courier vehicle, empty string otherwise.
        """
        parts = entity_id.split("_")
        # Courier vehicles have at least 3 parts: courier_id, vehicle_type, index
        if len(parts) >= 3:
            return parts[0]
        return ""
    
    def record_edge_completion(
        self,
        entity_id: str,
        distance: float,
        travel_time: float,
        monetary_cost: float = 0.0
    ) -> None:
        """Record completion of an edge traversal.

        Args:
            entity_id: Unique identifier of the vehicle.
            distance: Distance of the edge in meters.
            travel_time: Travel time in seconds.
            monetary_cost: Monetary cost in dollars for traversing the edge.
        """
        if entity_id not in self._vehicle_metrics:
            self._vehicle_metrics[entity_id] = VehicleMetrics()

        metrics = self._vehicle_metrics[entity_id]
        metrics.distance_traveled += distance
        metrics.travel_time += travel_time
        metrics.monetary_cost += monetary_cost
        metrics.edges_traversed += 1

        self._total_distance += distance
        self._total_travel_time += travel_time
        self._total_monetary_cost += monetary_cost

        # Also track courier-level metrics (excluding buses)
        courier_id = self._get_courier_id(entity_id)
        if courier_id:
            if courier_id not in self._courier_metrics:
                self._courier_metrics[courier_id] = VehicleMetrics()
            courier_metrics = self._courier_metrics[courier_id]
            courier_metrics.distance_traveled += distance
            courier_metrics.travel_time += travel_time
            courier_metrics.monetary_cost += monetary_cost
            courier_metrics.edges_traversed += 1
    
    def get_vehicle_metrics(self, entity_id: str) -> VehicleMetrics:
        """Get metrics for a specific vehicle.
        
        Args:
            entity_id: Vehicle identifier.
            
        Returns:
            VehicleMetrics object. Returns empty metrics if vehicle not found.
        """
        return self._vehicle_metrics.get(entity_id, VehicleMetrics())
    
    def get_total_distance(self) -> float:
        """Get total distance traveled by all vehicles."""
        return self._total_distance
    
    def get_total_travel_time(self) -> float:
        """Get total travel time for all vehicles."""
        return self._total_travel_time

    def get_total_monetary_cost(self) -> float:
        """Get total monetary cost for all vehicles."""
        return self._total_monetary_cost

    def get_all_vehicle_metrics(self) -> Dict[str, VehicleMetrics]:
        """Get metrics for all vehicles.
        
        Returns:
            Dictionary mapping entity_id to VehicleMetrics.
        """
        return dict(self._vehicle_metrics)
    
    def record_delivery_assignment(self, assigned: int, total: int) -> None:
        """Record delivery request assignment results.

        Args:
            assigned: Number of delivery requests successfully assigned.
            total: Total number of delivery requests.
        """
        self._delivery_requests_assigned = assigned
        self._delivery_requests_total = total

    def get_delivery_assignment_rate(self) -> float:
        """Get the proportion of delivery requests that were assigned.

        Returns:
            Float between 0.0 and 1.0 representing the assignment rate.
        """
        if self._delivery_requests_total == 0:
            return 0.0
        return self._delivery_requests_assigned / self._delivery_requests_total

    def record_delivery_completion(self, vehicle_id: str, courier_id: str, delivery_time: float) -> None:
        """Record that a delivery request has been completed (delivered).

        Args:
            vehicle_id: ID of the vehicle that made the delivery.
            courier_id: ID of the courier that owns the vehicle.
            delivery_time: Time taken to deliver the parcel in seconds.
        """
        self._delivery_requests_delivered += 1

        # Track delivery time per vehicle
        if vehicle_id not in self._vehicle_metrics:
            self._vehicle_metrics[vehicle_id] = VehicleMetrics()
        self._vehicle_metrics[vehicle_id].delivery_times.append(delivery_time)

        # Track delivery time per courier
        if courier_id:
            if courier_id not in self._courier_metrics:
                self._courier_metrics[courier_id] = VehicleMetrics()
            self._courier_metrics[courier_id].delivery_times.append(delivery_time)

    def get_delivery_completion_rate(self) -> float:
        """Get the proportion of assigned delivery requests that were delivered.

        Returns:
            Float between 0.0 and 1.0 representing the delivery completion rate
            relative to assigned requests.
        """
        if self._delivery_requests_assigned == 0:
            return 0.0
        return self._delivery_requests_delivered / self._delivery_requests_assigned

    def get_average_delivery_time(self) -> float:
        """Get the average delivery time across all vehicles.

        Returns:
            Average time in seconds from journey start to delivery.
        """
        all_times = []
        for metrics in self._vehicle_metrics.values():
            all_times.extend(metrics.delivery_times)
        if not all_times:
            return 0.0
        return sum(all_times) / len(all_times)

    def reset(self) -> None:
        """Clear all collected metrics."""
        self._vehicle_metrics.clear()
        self._courier_metrics.clear()
        self._total_distance = 0.0
        self._total_travel_time = 0.0
        self._total_monetary_cost = 0.0
        self._delivery_requests_total = 0
        self._delivery_requests_assigned = 0
        self._delivery_requests_delivered = 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics.

        Returns:
            Dictionary with totals, per-vehicle, and per-courier breakdown.
        """
        return {
            "total_distance": self._total_distance,
            "total_travel_time": self._total_travel_time,
            "total_monetary_cost": self._total_monetary_cost,
            "vehicle_count": len(self._vehicle_metrics),
            "courier_count": len(self._courier_metrics),
            "delivery_requests_total": self._delivery_requests_total,
            "delivery_requests_assigned": self._delivery_requests_assigned,
            "delivery_requests_delivered": self._delivery_requests_delivered,
            "delivery_assignment_rate": self.get_delivery_assignment_rate(),
            "delivery_completion_rate": self.get_delivery_completion_rate(),
            "average_delivery_time_s": self.get_average_delivery_time(),
            "vehicles": {
                entity_id: {
                    "distance": m.distance_traveled,
                    "travel_time": m.travel_time,
                    "monetary_cost": m.monetary_cost,
                    "edges": m.edges_traversed,
                    "avg_delivery_time_s": m.get_average_delivery_time(),
                    "deliveries_count": len(m.delivery_times),
                }
                for entity_id, m in self._vehicle_metrics.items()
            },
            "couriers": {
                courier_id: {
                    "distance": m.distance_traveled,
                    "travel_time": m.travel_time,
                    "monetary_cost": m.monetary_cost,
                    "edges": m.edges_traversed,
                    "avg_delivery_time_s": m.get_average_delivery_time(),
                    "deliveries_count": len(m.delivery_times),
                }
                for courier_id, m in self._courier_metrics.items()
            }
        }
    
    def print_summary(self) -> None:
        """Pretty print metrics summary to console."""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("SIMULATION METRICS SUMMARY")
        print("=" * 60)
        print(f"Total Vehicles: {summary['vehicle_count']}")
        print(f"Total Distance: {summary['total_distance']:.2f} m")
        print(f"Total Travel Time: {summary['total_travel_time']:.2f} s")
        print(f"Total Monetary Cost: ${summary['total_monetary_cost']:.2f}")
        print(f"Average Distance per Vehicle: {summary['total_distance'] / max(summary['vehicle_count'], 1):.2f} m")
        print("-" * 60)
        print("Per-Vehicle Breakdown:")
        print("-" * 60)
        print(f"{'Vehicle ID':<30} {'Distance (m)':<15} {'Time (s)':<12} {'Cost ($)':<10} {'Edges':<8}")
        print("-" * 60)
        for entity_id, m in summary["vehicles"].items():
            print(f"{entity_id:<30} {m['distance']:<15.2f} {m['travel_time']:<12.2f} {m['monetary_cost']:<10.2f} {m['edges']:<8}")
        if summary['couriers']:
            print("-" * 60)
            print("Per-Courier Breakdown (Aggregated across all vehicles):")
            print("-" * 60)
            print(f"{'Courier ID':<30} {'Distance (m)':<15} {'Time (s)':<12} {'Cost ($)':<10} {'Edges':<8}")
            print("-" * 60)
            for courier_id, m in summary["couriers"].items():
                print(f"{courier_id:<30} {m['distance']:<15.2f} {m['travel_time']:<12.2f} {m['monetary_cost']:<10.2f} {m['edges']:<8}")
        print("=" * 60 + "\n")
    
    def dump_to_csv(self) -> None:
        """Write metrics to CSV files in the output directory.

        Writes per-vehicle metrics to output/metrics_per_vehicle.csv,
        per-courier metrics to output/metrics_per_courier.csv,
        and aggregate totals to output/metrics_totals.csv.
        """
        os.makedirs("output", exist_ok=True)

        # Write per-vehicle metrics
        with open(os.path.join("output", self.vehicles_filename), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["entity_id", "distance_traveled_m", "travel_time_s", "monetary_cost_usd",
                           "edges_traversed", "deliveries_count", "avg_delivery_time_s"])
            for entity_id, metrics in self._vehicle_metrics.items():
                writer.writerow([
                    entity_id,
                    metrics.distance_traveled,
                    metrics.travel_time,
                    metrics.monetary_cost,
                    metrics.edges_traversed,
                    len(metrics.delivery_times),
                    metrics.get_average_delivery_time()
                ])

        # Write per-courier metrics
        with open(os.path.join("output", self.couriers_filename), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["courier_id", "total_distance_m", "total_travel_time_s", "total_monetary_cost_usd",
                           "total_edges_traversed", "deliveries_count", "avg_delivery_time_s"])
            for courier_id, metrics in self._courier_metrics.items():
                writer.writerow([
                    courier_id,
                    metrics.distance_traveled,
                    metrics.travel_time,
                    metrics.monetary_cost,
                    metrics.edges_traversed,
                    len(metrics.delivery_times),
                    metrics.get_average_delivery_time()
                ])

        # Write totals and aggregates
        with open(os.path.join("output", self.totals_filename), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value"])
            writer.writerow(["total_vehicles", len(self._vehicle_metrics)])
            writer.writerow(["total_couriers", len(self._courier_metrics)])
            writer.writerow(["total_distance_m", self._total_distance])
            writer.writerow(["total_travel_time_s", self._total_travel_time])
            writer.writerow(["total_monetary_cost_usd", self._total_monetary_cost])
            writer.writerow(["average_distance_per_vehicle_m",
                           self._total_distance / max(len(self._vehicle_metrics), 1)])
            writer.writerow(["average_travel_time_per_vehicle_s",
                           self._total_travel_time / max(len(self._vehicle_metrics), 1)])
            writer.writerow(["delivery_requests_total", self._delivery_requests_total])
            writer.writerow(["delivery_requests_assigned", self._delivery_requests_assigned])
            writer.writerow(["delivery_requests_delivered", self._delivery_requests_delivered])
            writer.writerow(["delivery_assignment_rate", self.get_delivery_assignment_rate()])
            writer.writerow(["delivery_completion_rate", self.get_delivery_completion_rate()])
            writer.writerow(["average_delivery_time_s", self.get_average_delivery_time()])
