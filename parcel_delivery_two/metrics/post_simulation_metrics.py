"""Post-simulation business metrics analyzer.

Analyzes simulation results from CSV files to calculate business and environmental metrics
such as operational costs, fuel consumption, and emissions. These metrics are decoupled
from the simulation runtime and can be calculated with different assumptions.
"""

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class VehicleTypeConfig:
    """Configuration for vehicle type business metrics.
    
    Args:
        fuel_efficiency_km_per_l: Distance traveled per liter of fuel (km/L).
            Higher values indicate better fuel economy. Use float('inf') for
            zero-emission vehicles (bikes, EVs).
        fuel_price_per_liter: Cost per liter of fuel in dollars.
        emission_factor_g_co2_per_l: Grams of CO2 emitted per liter of fuel.
            Gasoline: ~2300 g/L, Diesel: ~2600 g/L.
        is_clean_mode: Whether this vehicle type counts as clean transport
            for mode share calculations (bikes, EVs = True).
        labor_cost_per_hour: Driver labor cost per hour in dollars.
    
    Example:
        car_config = VehicleTypeConfig(
            fuel_efficiency_km_per_l=15.0,  # 6.7 L/100km
            fuel_price_per_liter=1.80,
            emission_factor_g_co2_per_l=2300,
            is_clean_mode=False,
            labor_cost_per_hour=25.0
        )
    """
    fuel_efficiency_km_per_l: float
    fuel_price_per_liter: float
    emission_factor_g_co2_per_l: float
    is_clean_mode: bool
    labor_cost_per_hour: float
    
    def calculate_fuel_consumption_l(self, distance_km: float) -> float:
        """Calculate fuel consumption for a given distance.
        
        Formula: distance_km / fuel_efficiency_km_per_l
        
        Args:
            distance_km: Distance traveled in kilometers.
            
        Returns:
            Fuel consumed in liters.
        """
        if self.fuel_efficiency_km_per_l == float('inf'):
            return 0.0
        return distance_km / self.fuel_efficiency_km_per_l
    
    def calculate_fuel_cost(self, distance_km: float) -> float:
        """Calculate fuel cost for a given distance.
        
        Formula: fuel_consumption_l × fuel_price_per_liter
        
        Args:
            distance_km: Distance traveled in kilometers.
            
        Returns:
            Fuel cost in dollars.
        """
        fuel_l = self.calculate_fuel_consumption_l(distance_km)
        return fuel_l * self.fuel_price_per_liter
    
    def calculate_emissions_kg(self, distance_km: float) -> float:
        """Calculate CO2 emissions for a given distance.
        
        Formula: fuel_consumption_l × emission_factor_g_co2_per_l / 1000
        
        Args:
            distance_km: Distance traveled in kilometers.
            
        Returns:
            CO2 emissions in kilograms.
        """
        fuel_l = self.calculate_fuel_consumption_l(distance_km)
        emissions_g = fuel_l * self.emission_factor_g_co2_per_l
        return emissions_g / 1000.0
    
    def calculate_emission_intensity_kg_per_km(self) -> float:
        """Calculate emission intensity (emissions per km).
        
        Formula: emission_factor_g_co2_per_l / fuel_efficiency_km_per_l / 1000
        
        Returns:
            Emission intensity in kg CO2 per km.
        """
        if self.fuel_efficiency_km_per_l == float('inf'):
            return 0.0
        return (self.emission_factor_g_co2_per_l / self.fuel_efficiency_km_per_l) / 1000.0
    
    def calculate_labor_cost(self, travel_time_hours: float) -> float:
        """Calculate labor cost for given travel time.
        
        Formula: travel_time_hours × labor_cost_per_hour
        
        Args:
            travel_time_hours: Time traveled in hours.
            
        Returns:
            Labor cost in dollars.
        """
        return travel_time_hours * self.labor_cost_per_hour


@dataclass
class VehicleMetricsRow:
    """Parsed row from metrics_per_vehicle.csv."""
    entity_id: str
    distance_m: float
    travel_time_s: float
    monetary_cost_usd: float
    edges_traversed: int
    deliveries_count: int
    avg_delivery_time_s: float
    
    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.distance_m / 1000.0
    
    @property
    def travel_time_hours(self) -> float:
        """Travel time in hours."""
        return self.travel_time_s / 3600.0
    
    def get_vehicle_type(self) -> str:
        """Extract vehicle type from entity_id.
        
        Entity ID format: "{courier_id}_{vehicle_type}_{index}" for courier vehicles
        or "{entity_type}_{index}" for other entities (e.g., "bus_263").
        
        Returns:
            Vehicle type string (e.g., "car", "bike", "bus").
        """
        parts = self.entity_id.split("_")
        if len(parts) >= 3:
            # Courier vehicle: courier1_car_0 -> car
            return parts[1]
        elif len(parts) == 2:
            # Other entity: bus_263 -> bus
            return parts[0]
        return "unknown"


@dataclass
class CourierMetricsRow:
    """Parsed row from metrics_per_courier.csv."""
    courier_id: str
    total_distance_m: float
    total_travel_time_s: float
    total_monetary_cost_usd: float
    total_edges_traversed: int
    deliveries_count: int
    avg_delivery_time_s: float
    
    @property
    def distance_km(self) -> float:
        """Distance in kilometers."""
        return self.total_distance_m / 1000.0
    
    @property
    def travel_time_hours(self) -> float:
        """Travel time in hours."""
        return self.total_travel_time_s / 3600.0


@dataclass
class TotalsMetricsRow:
    """Parsed row from metrics_totals.csv."""
    metric: str
    value: float


class PostSimulationMetrics:
    """Post-simulation business metrics analyzer.
    
    Calculates business and environmental metrics from simulation CSV outputs.
    Uses configurable vehicle type assumptions for cost and emission calculations.
    
    Example:
        configs = {
            "car": VehicleTypeConfig(fuel_efficiency_km_per_l=15.0, ...),
            "bike": VehicleTypeConfig(fuel_efficiency_km_per_l=float('inf'), ...),
        }
        
        analyzer = PostSimulationMetrics.from_csvs("output/", configs)
        print(f"Total operational cost: ${analyzer.total_operational_cost():.2f}")
        print(f"Emissions: {analyzer.total_emissions_kg_co2():.2f} kg CO2")
        analyzer.dump_to_csv()
    
    Args:
        vehicle_configs: Mapping from vehicle type to configuration.
        vehicle_data: List of per-vehicle metrics from simulation.
        courier_data: List of per-courier metrics from simulation.
        totals_data: Dictionary of aggregate metrics from simulation.
    """
    
    def __init__(
        self,
        vehicle_configs: Dict[str, VehicleTypeConfig],
        vehicle_data: List[VehicleMetricsRow],
        courier_data: List[CourierMetricsRow],
        totals_data: Dict[str, float]
    ):
        self.vehicle_configs = vehicle_configs
        self.vehicle_data = vehicle_data
        self.courier_data = courier_data
        self.totals_data = totals_data
        
        # Build lookup by vehicle type for efficient filtering
        self._vehicles_by_type: Dict[str, List[VehicleMetricsRow]] = {}
        for vehicle in vehicle_data:
            vtype = vehicle.get_vehicle_type()
            if vtype not in self._vehicles_by_type:
                self._vehicles_by_type[vtype] = []
            self._vehicles_by_type[vtype].append(vehicle)
    
    @classmethod
    def from_csvs(
        cls,
        output_dir: str,
        vehicle_configs: Dict[str, VehicleTypeConfig]
    ) -> "PostSimulationMetrics":
        """Create analyzer from simulation output CSV files.
        
        Reads metrics from:
        - {output_dir}/metrics_per_vehicle.csv
        - {output_dir}/metrics_per_courier.csv
        - {output_dir}/metrics_totals.csv
        
        Args:
            output_dir: Directory containing simulation output CSVs.
            vehicle_configs: Configuration for each vehicle type.
            
        Returns:
            Initialized PostSimulationMetrics instance.
            
        Raises:
            FileNotFoundError: If required CSV files are not found.
        """
        output_path = Path(output_dir)
        
        # Read per-vehicle metrics
        vehicle_data = []
        vehicle_csv = output_path / "metrics_per_vehicle.csv"
        with open(vehicle_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vehicle_data.append(VehicleMetricsRow(
                    entity_id=row["entity_id"],
                    distance_m=float(row["distance_traveled_m"]),
                    travel_time_s=float(row["travel_time_s"]),
                    monetary_cost_usd=float(row["monetary_cost_usd"]),
                    edges_traversed=int(row["edges_traversed"]),
                    deliveries_count=int(row["deliveries_count"]),
                    avg_delivery_time_s=float(row["avg_delivery_time_s"])
                ))
        
        # Read per-courier metrics
        courier_data = []
        courier_csv = output_path / "metrics_per_courier.csv"
        with open(courier_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                courier_data.append(CourierMetricsRow(
                    courier_id=row["courier_id"],
                    total_distance_m=float(row["total_distance_m"]),
                    total_travel_time_s=float(row["total_travel_time_s"]),
                    total_monetary_cost_usd=float(row["total_monetary_cost_usd"]),
                    total_edges_traversed=int(row["total_edges_traversed"]),
                    deliveries_count=int(row["deliveries_count"]),
                    avg_delivery_time_s=float(row["avg_delivery_time_s"])
                ))
        
        # Read totals
        totals_data = {}
        totals_csv = output_path / "metrics_totals.csv"
        with open(totals_csv, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                totals_data[row["metric"]] = float(row["value"])
        
        return cls(vehicle_configs, vehicle_data, courier_data, totals_data)
    
    # ========== AGGREGATE METRICS ==========
    
    def total_distance_km(self) -> float:
        """Total distance traveled by all vehicles.
        
        Returns:
            Total distance in kilometers.
        """
        return sum(v.distance_km for v in self.vehicle_data)
    
    def total_travel_time_hours(self) -> float:
        """Total travel time by all vehicles.
        
        Returns:
            Total travel time in hours.
        """
        return sum(v.travel_time_hours for v in self.vehicle_data)
    
    def total_deliveries(self) -> int:
        """Total number of deliveries completed.
        
        Returns:
            Total delivery count.
        """
        return sum(v.deliveries_count for v in self.vehicle_data)
    
    def total_congestion_cost(self) -> float:
        """Total congestion pricing cost from simulation.
        
        Returns:
            Total congestion cost in dollars.
        """
        return sum(v.monetary_cost_usd for v in self.vehicle_data)
    
    # ========== FUEL METRICS ==========
    
    def total_fuel_consumption_l(self) -> float:
        """Total fuel consumed across all vehicles.
        
        Formula: Σ (distance_km / fuel_efficiency_km_per_l) for each vehicle
        
        Returns:
            Total fuel consumption in liters.
        """
        total = 0.0
        for vehicle in self.vehicle_data:
            vtype = vehicle.get_vehicle_type()
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                total += config.calculate_fuel_consumption_l(vehicle.distance_km)
        return total
    
    def fuel_consumption_by_type_l(self) -> Dict[str, float]:
        """Fuel consumption broken down by vehicle type.
        
        Returns:
            Dictionary mapping vehicle type to fuel consumption in liters.
        """
        result = {}
        for vtype, vehicles in self._vehicles_by_type.items():
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                result[vtype] = sum(
                    config.calculate_fuel_consumption_l(v.distance_km)
                    for v in vehicles
                )
        return result
    
    def fleet_fuel_efficiency_km_per_l(self) -> float:
        """Fleet average fuel efficiency.
        
        Formula: total_distance_km / total_fuel_consumption_l
        
        Returns:
            Fleet fuel efficiency in km/L. Returns infinity if no fuel consumed.
        """
        fuel_l = self.total_fuel_consumption_l()
        if fuel_l == 0:
            return float('inf')
        return self.total_distance_km() / fuel_l
    
    def total_fuel_cost(self) -> float:
        """Total fuel cost across all vehicles.
        
        Formula: Σ (fuel_consumption_l × fuel_price_per_liter) for each vehicle
        
        Returns:
            Total fuel cost in dollars.
        """
        total = 0.0
        for vehicle in self.vehicle_data:
            vtype = vehicle.get_vehicle_type()
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                total += config.calculate_fuel_cost(vehicle.distance_km)
        return total
    
    def fuel_cost_per_km(self) -> float:
        """Average fuel cost per kilometer.
        
        Formula: total_fuel_cost / total_distance_km
        
        Returns:
            Fuel cost per km in $/km. Returns 0 if no distance traveled.
        """
        distance = self.total_distance_km()
        if distance == 0:
            return 0.0
        return self.total_fuel_cost() / distance
    
    # ========== EMISSION METRICS ==========
    
    def total_emissions_kg_co2(self) -> float:
        """Total CO2 emissions across all vehicles.
        
        Formula: Σ (fuel_consumption_l × emission_factor_g_co2_per_l / 1000)
        
        Returns:
            Total CO2 emissions in kilograms.
        """
        total = 0.0
        for vehicle in self.vehicle_data:
            vtype = vehicle.get_vehicle_type()
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                total += config.calculate_emissions_kg(vehicle.distance_km)
        return total
    
    def emissions_by_type_kg(self) -> Dict[str, float]:
        """Emissions broken down by vehicle type.
        
        Returns:
            Dictionary mapping vehicle type to emissions in kg CO2.
        """
        result = {}
        for vtype, vehicles in self._vehicles_by_type.items():
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                result[vtype] = sum(
                    config.calculate_emissions_kg(v.distance_km)
                    for v in vehicles
                )
        return result
    
    def fleet_emission_factor_g_per_km(self) -> float:
        """Fleet average emission factor.
        
        Formula: (total_emissions_kg × 1000) / total_distance_km
        
        Returns:
            Fleet emission factor in g CO2 per km. Returns 0 if no distance.
        """
        distance = self.total_distance_km()
        if distance == 0:
            return 0.0
        return (self.total_emissions_kg_co2() * 1000) / distance
    
    def emissions_per_delivery_kg(self) -> float:
        """Average emissions per delivery.
        
        Formula: total_emissions_kg_co2 / total_deliveries
        
        Returns:
            Emissions per delivery in kg CO2. Returns 0 if no deliveries.
        """
        deliveries = self.total_deliveries()
        if deliveries == 0:
            return 0.0
        return self.total_emissions_kg_co2() / deliveries
    
    # ========== COST METRICS ==========
    
    def total_labor_cost(self) -> float:
        """Total labor cost across all vehicles.
        
        Formula: Σ (travel_time_hours × labor_cost_per_hour) for each vehicle
        
        Returns:
            Total labor cost in dollars.
        """
        total = 0.0
        for vehicle in self.vehicle_data:
            vtype = vehicle.get_vehicle_type()
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                total += config.calculate_labor_cost(vehicle.travel_time_hours)
        return total
    
    def total_operational_cost(self) -> float:
        """Total operational cost (fuel + labor + congestion).
        
        Formula: total_fuel_cost + total_labor_cost + total_congestion_cost
        
        Returns:
            Total operational cost in dollars.
        """
        return self.total_fuel_cost() + self.total_labor_cost() + self.total_congestion_cost()
    
    def cost_breakdown(self) -> Dict[str, float]:
        """Breakdown of operational costs by category.
        
        Returns:
            Dictionary with keys: fuel, labor, congestion, total
        """
        fuel = self.total_fuel_cost()
        labor = self.total_labor_cost()
        congestion = self.total_congestion_cost()
        return {
            "fuel": fuel,
            "labor": labor,
            "congestion": congestion,
            "total": fuel + labor + congestion
        }
    
    def cost_per_delivery(self) -> float:
        """Average cost per delivery.
        
        Formula: total_operational_cost / total_deliveries
        
        Returns:
            Cost per delivery in dollars. Returns 0 if no deliveries.
        """
        deliveries = self.total_deliveries()
        if deliveries == 0:
            return 0.0
        return self.total_operational_cost() / deliveries
    
    def cost_per_km(self) -> float:
        """Average operational cost per kilometer.
        
        Formula: total_operational_cost / total_distance_km
        
        Returns:
            Cost per km in $/km. Returns 0 if no distance.
        """
        distance = self.total_distance_km()
        if distance == 0:
            return 0.0
        return self.total_operational_cost() / distance
    
    # ========== MODE SHARE METRICS ==========
    
    def clean_mode_share(self) -> float:
        """Proportion of deliveries completed by clean transport modes.

        Formula: clean_deliveries / total_deliveries

        Clean modes are those with is_clean_mode=True in their config.

        Returns:
            Clean mode share as ratio 0-1. Returns 0 if no deliveries.
        """
        total_deliveries = self.total_deliveries()
        if total_deliveries == 0:
            return 0.0

        clean_deliveries = 0
        for vtype, vehicles in self._vehicles_by_type.items():
            if vtype in self.vehicle_configs:
                config = self.vehicle_configs[vtype]
                if config.is_clean_mode:
                    clean_deliveries += sum(v.deliveries_count for v in vehicles)

        return clean_deliveries / total_deliveries
    
    def distance_by_type_km(self) -> Dict[str, float]:
        """Distance traveled by each vehicle type.
        
        Returns:
            Dictionary mapping vehicle type to distance in km.
        """
        return {
            vtype: sum(v.distance_km for v in vehicles)
            for vtype, vehicles in self._vehicles_by_type.items()
        }
    
    def deliveries_by_type(self) -> Dict[str, int]:
        """Delivery count by each vehicle type.
        
        Returns:
            Dictionary mapping vehicle type to delivery count.
        """
        return {
            vtype: sum(v.deliveries_count for v in vehicles)
            for vtype, vehicles in self._vehicles_by_type.items()
        }
    
    # ========== SUMMARY & OUTPUT ==========
    
    def get_summary(self) -> Dict:
        """Get complete summary of all business metrics.
        
        Returns:
            Dictionary with all metrics organized by category.
        """
        return {
            "distance": {
                "total_km": self.total_distance_km(),
                "by_type_km": self.distance_by_type_km(),
            },
            "fuel": {
                "total_consumption_l": self.total_fuel_consumption_l(),
                "by_type_l": self.fuel_consumption_by_type_l(),
                "fleet_efficiency_km_per_l": self.fleet_fuel_efficiency_km_per_l(),
                "total_cost_usd": self.total_fuel_cost(),
                "cost_per_km_usd": self.fuel_cost_per_km(),
            },
            "emissions": {
                "total_kg_co2": self.total_emissions_kg_co2(),
                "by_type_kg": self.emissions_by_type_kg(),
                "fleet_factor_g_per_km": self.fleet_emission_factor_g_per_km(),
                "per_delivery_kg": self.emissions_per_delivery_kg(),
            },
            "costs": {
                "fuel_usd": self.total_fuel_cost(),
                "labor_usd": self.total_labor_cost(),
                "congestion_usd": self.total_congestion_cost(),
                "total_operational_usd": self.total_operational_cost(),
                "per_delivery_usd": self.cost_per_delivery(),
                "per_km_usd": self.cost_per_km(),
                "breakdown": self.cost_breakdown(),
            },
            "mode_share": {
                "clean_share_ratio": self.clean_mode_share(),
                "distance_by_type_km": self.distance_by_type_km(),
                "deliveries_by_type": self.deliveries_by_type(),
                "total_deliveries": self.total_deliveries(),
            },
            "time": {
                "total_travel_hours": self.total_travel_time_hours(),
            }
        }
    
    def print_summary(self) -> None:
        """Pretty print business metrics summary to console."""
        summary = self.get_summary()
        
        print("\n" + "=" * 70)
        print("POST-SIMULATION BUSINESS METRICS")
        print("=" * 70)
        
        # Distance
        print("\n📏 DISTANCE")
        print("-" * 70)
        print(f"Total Distance: {summary['distance']['total_km']:.2f} km")
        print("\nBy Vehicle Type:")
        for vtype, dist in summary['distance']['by_type_km'].items():
            pct = (dist / summary['distance']['total_km'] * 100) if summary['distance']['total_km'] > 0 else 0
            print(f"  {vtype:<15} {dist:>10.2f} km ({pct:>5.1f}%)")
        
        # Fuel
        print("\n⛽ FUEL")
        print("-" * 70)
        print(f"Total Consumption: {summary['fuel']['total_consumption_l']:.2f} L")
        print(f"Fleet Efficiency: {summary['fuel']['fleet_efficiency_km_per_l']:.2f} km/L")
        print(f"Fuel Cost: ${summary['fuel']['total_cost_usd']:.2f}")
        print(f"Fuel Cost per km: ${summary['fuel']['cost_per_km_usd']:.4f}/km")
        print("\nBy Vehicle Type:")
        for vtype, fuel in summary['fuel']['by_type_l'].items():
            print(f"  {vtype:<15} {fuel:>10.2f} L")
        
        # Emissions
        print("\n🌱 EMISSIONS")
        print("-" * 70)
        print(f"Total Emissions: {summary['emissions']['total_kg_co2']:.2f} kg CO2")
        print(f"Fleet Emission Factor: {summary['emissions']['fleet_factor_g_per_km']:.2f} g/km")
        print(f"Emissions per Delivery: {summary['emissions']['per_delivery_kg']:.3f} kg/delivery")
        print("\nBy Vehicle Type:")
        for vtype, emissions in summary['emissions']['by_type_kg'].items():
            print(f"  {vtype:<15} {emissions:>10.2f} kg CO2")
        
        # Costs
        print("\n💰 COSTS")
        print("-" * 70)
        breakdown = summary['costs']['breakdown']
        print(f"Fuel:           ${breakdown['fuel']:>10.2f}")
        print(f"Labor:          ${breakdown['labor']:>10.2f}")
        print(f"Congestion:     ${breakdown['congestion']:>10.2f}")
        print(f"{'-'*35}")
        print(f"Total:          ${breakdown['total']:>10.2f}")
        print(f"Per Delivery:   ${summary['costs']['per_delivery_usd']:.2f}")
        print(f"Per km:         ${summary['costs']['per_km_usd']:.4f}")
        
        # Mode Share
        print("\n🚲 MODE SHARE")
        print("-" * 70)
        clean_pct = summary['mode_share']['clean_share_ratio'] * 100
        print(f"Clean Transport Share: {clean_pct:.1f}%")
        print(f"Total Deliveries: {summary['mode_share']['total_deliveries']}")
        print("\nBy Vehicle Type:")
        for vtype, count in summary['mode_share']['deliveries_by_type'].items():
            pct = (count / summary['mode_share']['total_deliveries'] * 100) if summary['mode_share']['total_deliveries'] > 0 else 0
            print(f"  {vtype:<15} {count:>8} deliveries ({pct:>5.1f}%)")
        
        print("\n" + "=" * 70 + "\n")
    
    def dump_to_csv(self, output_path: str = "output/business_metrics.csv") -> None:
        """Write business metrics to CSV file.
        
        Args:
            output_path: Path for output CSV file.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        summary = self.get_summary()
        
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["metric", "value", "unit"])
            
            # Distance
            writer.writerow(["total_distance_km", summary['distance']['total_km'], "km"])
            for vtype, dist in summary['distance']['by_type_km'].items():
                writer.writerow([f"distance_{vtype}_km", dist, "km"])
            
            # Fuel
            writer.writerow(["total_fuel_consumption_l", summary['fuel']['total_consumption_l'], "L"])
            writer.writerow(["fleet_fuel_efficiency_km_per_l", summary['fuel']['fleet_efficiency_km_per_l'], "km/L"])
            writer.writerow(["total_fuel_cost_usd", summary['fuel']['total_cost_usd'], "$"])
            writer.writerow(["fuel_cost_per_km_usd", summary['fuel']['cost_per_km_usd'], "$/km"])
            for vtype, fuel in summary['fuel']['by_type_l'].items():
                writer.writerow([f"fuel_consumption_{vtype}_l", fuel, "L"])
            
            # Emissions
            writer.writerow(["total_emissions_kg_co2", summary['emissions']['total_kg_co2'], "kg"])
            writer.writerow(["fleet_emission_factor_g_co2_per_km", summary['emissions']['fleet_factor_g_per_km'], "g/km"])
            writer.writerow(["emissions_per_delivery_kg", summary['emissions']['per_delivery_kg'], "kg"])
            for vtype, emissions in summary['emissions']['by_type_kg'].items():
                writer.writerow([f"emissions_{vtype}_kg", emissions, "kg"])
            
            # Costs
            writer.writerow(["fuel_cost_usd", summary['costs']['fuel_usd'], "$"])
            writer.writerow(["labor_cost_usd", summary['costs']['labor_usd'], "$"])
            writer.writerow(["congestion_cost_usd", summary['costs']['congestion_usd'], "$"])
            writer.writerow(["total_operational_cost_usd", summary['costs']['total_operational_usd'], "$"])
            writer.writerow(["cost_per_delivery_usd", summary['costs']['per_delivery_usd'], "$"])
            writer.writerow(["cost_per_km_usd", summary['costs']['per_km_usd'], "$/km"])
            
            # Mode Share
            writer.writerow(["clean_mode_share_ratio", summary['mode_share']['clean_share_ratio'], "ratio"])
            writer.writerow(["total_deliveries", summary['mode_share']['total_deliveries'], "count"])
            for vtype, count in summary['mode_share']['deliveries_by_type'].items():
                writer.writerow([f"deliveries_{vtype}", count, "count"])
