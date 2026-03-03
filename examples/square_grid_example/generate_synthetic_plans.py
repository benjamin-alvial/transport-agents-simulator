"""Generate synthetic MATSim plans with user-specified work link locations."""

import random
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Optional


def generate_plans(
    work_links: List[int],
    num_persons: int = 500,
    total_links: int = 1680,
    morning_start: int = 8 * 3600,  # 8:00 AM
    morning_end: int = 9 * 3600,   # 9:00 AM
    work_duration_min: int = 8 * 3600,  # 8 hours
    work_duration_max: int = 9 * 3600,  # 9 hours
    output_file: str = "synthetic_plans.xml",
    seed: int = 42
) -> None:
    """Generate synthetic MATSim plans with specified work locations.
    
    Home locations are randomly assigned from all available links.
    Work locations are randomly chosen from the user-specified list.
    
    Args:
        work_links: List of link IDs where work activities occur (required).
        num_persons: Number of persons/agents to generate.
        total_links: Total number of links in the network (default 1680 for 21x21 grid).
        morning_start: Earliest departure time in seconds (default 6:00 AM).
        morning_end: Latest departure time in seconds (default 10:00 AM).
        work_duration_min: Minimum work duration in seconds (default 6 hours).
        work_duration_max: Maximum work duration in seconds (default 8 hours).
        output_file: Path to save the plans XML file.
        seed: Random seed for reproducibility.
    """
    random.seed(seed)
    
    # Ensure work links are valid
    work_links = [link for link in work_links if 0 <= link < total_links]
    if not work_links:
        raise ValueError(f"No valid work links provided. Must be in range [0, {total_links})")
    
    # Convert times to HH:MM format
    def secs_to_time(secs: int) -> str:
        h = secs // 3600
        m = (secs % 3600) // 60
        return f"{h:02d}:{m:02d}"
    
    # Create XML structure
    root = ET.Element("plans")
    root.set("xml:lang", "en")
    
    for i in range(num_persons):
        person = ET.SubElement(root, "person")
        person.set("id", f"commuter_{i}")
        
        plan = ET.SubElement(person, "plan")
        
        # Home location - random link from anywhere
        home_link = random.randint(0, total_links - 1)
        
        # Work location - randomly chosen from specified work links
        work_link = random.choice(work_links)
        
        # Morning departure
        morning_departure = random.randint(morning_start, morning_end)
        
        # Work duration
        work_duration = random.randint(work_duration_min, work_duration_max)
        
        # Home activity (morning)
        act_home_morning = ET.SubElement(plan, "act")
        act_home_morning.set("type", "h")
        act_home_morning.set("link", str(home_link))
        act_home_morning.set("end_time", secs_to_time(morning_departure))
        
        # Leg to work
        leg_to_work = ET.SubElement(plan, "leg")
        leg_to_work.set("mode", "car")
        
        # Work activity
        act_work = ET.SubElement(plan, "act")
        act_work.set("type", "w")
        act_work.set("link", str(work_link))
        act_work.set("dur", secs_to_time(work_duration))
        
        # Leg home
        leg_to_home = ET.SubElement(plan, "leg")
        leg_to_home.set("mode", "car")
        
        # Home activity (evening)
        act_home_evening = ET.SubElement(plan, "act")
        act_home_evening.set("type", "h")
        act_home_evening.set("link", str(home_link))
    
    # Pretty print XML
    xml_str = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="\t")
    
    # Add DOCTYPE
    lines = pretty_xml.split('\n')
    lines.insert(1, '<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">')
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Generated {num_persons} commuters")
    print(f"Work links: {len(work_links)} locations")
    print(f"Work link IDs: {work_links[:10]}{'...' if len(work_links) > 10 else ''}")
    print(f"Morning departures: {secs_to_time(morning_start)}-{secs_to_time(morning_end)}")
    print(f"Work duration: {secs_to_time(work_duration_min)}-{secs_to_time(work_duration_max)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    # Example: User-specified work links near bottom-right corner
    generate_plans(
        work_links=[1639],  # Last 50 links near bottom-right corner
        num_persons=500,
        total_links=1680,
        output_file="synthetic_plans.xml"
    )
