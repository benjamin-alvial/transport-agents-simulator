# Business Metrics Formulas

This document details the formulas used by `PostSimulationMetrics` for calculating post-simulation business and environmental metrics.

## Overview

The `PostSimulationMetrics` class analyzes simulation outputs (CSV files) to compute real-world business metrics including operational costs, fuel consumption, and emissions. These metrics are calculated **after** the simulation completes using configurable assumptions for each vehicle type.

---

## Vehicle Configuration

Each vehicle type is configured with fuel efficiency, costs, and emission factors:

```python
VehicleTypeConfig(
    fuel_efficiency_km_per_l=15.0,       # km traveled per liter
    fuel_price_per_liter=1.80,           # $ per liter
    emission_factor_g_co2_per_l=2300,    # g CO2 per liter
    is_clean_mode=False,                  # counts as clean transport?
    labor_cost_per_hour=25.0              # $ per hour
)
```

---

## Fuel Metrics

### Fuel Consumption
**Formula:**
```
fuel_consumption_l = distance_km / fuel_efficiency_km_per_l
```

**Unit:** Liters (L)

**Example:**
- Distance: 54 km
- Efficiency: 15 km/L
- Fuel: 54 / 15 = **3.6 L**

### Fleet Fuel Efficiency
**Formula:**
```
fleet_efficiency_km_per_l = total_distance_km / total_fuel_consumption_l
```

**Unit:** km/L

**Example:**
- Total distance: 166 km
- Total fuel: 13.7 L
- Efficiency: 166 / 13.7 = **12.1 km/L**

### Fuel Cost
**Formula:**
```
fuel_cost_usd = fuel_consumption_l × fuel_price_per_liter
```

**Unit:** $

**Example:**
- Fuel: 3.6 L
- Price: $1.80/L
- Cost: 3.6 × 1.80 = **$6.48**

### Fuel Cost per km
**Formula:**
```
fuel_cost_per_km_usd = total_fuel_cost_usd / total_distance_km
```

**Unit:** $/km

---

## Emission Metrics

### Total Emissions
**Formula:**
```
emissions_kg_co2 = fuel_consumption_l × emission_factor_g_co2_per_l / 1000
```

**Unit:** kg CO2

**Example:**
- Fuel: 3.6 L
- Emission factor: 2300 g CO2/L
- Emissions: 3.6 × 2300 / 1000 = **8.28 kg CO2**

### Emission Intensity
**Formula:**
```
emission_intensity_kg_per_km = emission_factor_g_co2_per_l / fuel_efficiency_km_per_l / 1000
```

**Unit:** kg CO2/km

**Example:**
- Emission factor: 2300 g/L
- Efficiency: 15 km/L
- Intensity: 2300 / 15 / 1000 = **0.153 kg/km**

### Fleet Emission Factor
**Formula:**
```
fleet_emission_factor_g_per_km = (total_emissions_kg_co2 × 1000) / total_distance_km
```

**Unit:** g CO2/km

**Example:**
- Total emissions: 34.54 kg
- Total distance: 166 km
- Factor: (34.54 × 1000) / 166 = **208.1 g/km**

### Emissions per Delivery
**Formula:**
```
emissions_per_delivery_kg = total_emissions_kg_co2 / total_deliveries
```

**Unit:** kg CO2/delivery

**Example:**
- Total emissions: 34.54 kg
- Deliveries: 90
- Per delivery: 34.54 / 90 = **0.384 kg/delivery**

---

## Cost Metrics

### Labor Cost
**Formula:**
```
labor_cost_usd = travel_time_hours × labor_cost_per_hour
```

**Unit:** $

**Conversion:**
- travel_time_hours = travel_time_seconds / 3600

### Total Operational Cost
**Formula:**
```
total_operational_cost_usd = fuel_cost + labor_cost + congestion_cost
```

**Unit:** $

**Components:**
- `fuel_cost`: Calculated from fuel consumption
- `labor_cost`: Driver wages based on travel time
- `congestion_cost`: From simulation (congestion pricing)

### Cost per Delivery
**Formula:**
```
cost_per_delivery_usd = total_operational_cost_usd / total_deliveries
```

**Unit:** $/delivery

### Cost per km
**Formula:**
```
cost_per_km_usd = total_operational_cost_usd / total_distance_km
```

**Unit:** $/km

---

## Mode Share Metrics

### Clean Mode Share
**Formula:**
```
clean_mode_share = clean_deliveries / total_deliveries
```

**Unit:** Ratio (0-1)

Where `clean_deliveries` is the sum of delivery counts for vehicle types with `is_clean_mode=True`.

**Example:**
- Bike deliveries: 10 (clean)
- Total deliveries: 90
- Clean share: 10 / 90 = **11.1%**

### Distance by Type
**Formula:**
```
distance_by_type_km[vehicle_type] = Σ distance_km for all vehicles of type
```

**Unit:** km

### Deliveries by Type
**Formula:**
```
deliveries_by_type[vehicle_type] = Σ deliveries_count for all vehicles of type
```

**Unit:** Count

---

## Example Vehicle Configurations

### Car
```python
car = VehicleTypeConfig(
    fuel_efficiency_km_per_l=15.0,      # ~6.7 L/100km
    fuel_price_per_liter=1.80,
    emission_factor_g_co2_per_l=2300,    # Gasoline
    is_clean_mode=False,
    labor_cost_per_hour=25.0
)
```

### Bike (Zero-Emission)
```python
bike = VehicleTypeConfig(
    fuel_efficiency_km_per_l=float('inf'),  # No fuel consumption
    fuel_price_per_liter=0.0,
    emission_factor_g_co2_per_l=0,
    is_clean_mode=True,
    labor_cost_per_hour=18.0
)
```

### Truck
```python
truck = VehicleTypeConfig(
    fuel_efficiency_km_per_l=8.0,       # ~12.5 L/100km
    fuel_price_per_liter=1.80,
    emission_factor_g_co2_per_l=2600,    # Diesel
    is_clean_mode=False,
    labor_cost_per_hour=30.0
)
```

### Big Truck
```python
bigtruck = VehicleTypeConfig(
    fuel_efficiency_km_per_l=5.0,       # ~20 L/100km
    fuel_price_per_liter=1.80,
    emission_factor_g_co2_per_l=2600,
    is_clean_mode=False,
    labor_cost_per_hour=35.0
)
```

### Bus
```python
bus = VehicleTypeConfig(
    fuel_efficiency_km_per_l=4.0,       # ~25 L/100km
    fuel_price_per_liter=1.80,
    emission_factor_g_co2_per_l=2600,
    is_clean_mode=False,
    labor_cost_per_hour=40.0
)
```

---

## Usage Example

```python
from parcel_delivery_two.metrics import PostSimulationMetrics, VehicleTypeConfig

# Define vehicle configurations
configs = {
    "car": VehicleTypeConfig(fuel_efficiency_km_per_l=15.0, ...),
    "bike": VehicleTypeConfig(fuel_efficiency_km_per_l=float('inf'), ...),
}

# Analyze simulation results
analyzer = PostSimulationMetrics.from_csvs("output/", configs)

# Get metrics
print(f"Total cost: ${analyzer.total_operational_cost():.2f}")
print(f"Emissions: {analyzer.total_emissions_kg_co2():.2f} kg CO2")
print(f"Clean mode share: {analyzer.clean_mode_share()*100:.1f}%")

# Export to CSV
analyzer.dump_to_csv("output/business_metrics.csv")
```

---

## Output Files

The analyzer produces `business_metrics.csv` with columns:
- `metric`: Metric name
- `value`: Calculated value
- `unit`: Unit of measurement

See example output in `examples/full_example/output/business_metrics.csv`.
