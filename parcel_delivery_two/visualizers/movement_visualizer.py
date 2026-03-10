from typing import Dict, List, Optional, Tuple

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.utils.time_utils import format_time

# Type alias
_Segment = Tuple[float, float, int, int]  # (t_entry, t_exit, from_node, to_node)

# Shape assignments: 5 distinct shapes for couriers
_COURIER_SHAPES = ["o", "s", "^", "D", "v"]  # circle, square, triangle up, diamond, triangle down


def _get_entity_shape(entity_id: str) -> str:
    """Determine marker shape based on entity type and courier assignment.
    
    Buses always use triangle up. Vehicles are assigned shapes based on
    their courier ID to visually group vehicles from the same courier.
    
    Args:
        entity_id: The entity identifier string.
        
    Returns:
        Matplotlib marker character.
    """
    if entity_id.startswith("bus"):
        return "^"
    
    # Extract courier number from entity_id
    # Expected formats: "courier_1", "courier_1_vehicle_0", "courier_2_car_0", etc.
    if "courier_" in entity_id:
        # Parse courier number
        parts = entity_id.split("_")
        for i, part in enumerate(parts):
            if part == "courier" and i + 1 < len(parts):
                try:
                    courier_num = int(parts[i + 1])
                    return _COURIER_SHAPES[courier_num % len(_COURIER_SHAPES)]
                except (ValueError, IndexError):
                    pass
    
    # Default shape for other entities
    return "o"


class MovementVisualizer:
    """Visualises entity movements on a network using EdgeLogger data.

    Reads the in-memory edge log and produces either an auto-playing animation
    (:meth:`animate`) or a manually-controlled slider view (:meth:`visualize`).
    Each entity is a coloured dot that moves along edges interpolated between
    entry and exit times. Buses are drawn as triangles, vehicles as circles.

    Args:
        network: The road network providing node positions.
        logger: The EdgeLogger instance to read from. Defaults to the
            singleton ``EdgeLogger()``.

    Example::

        sim.run(until=86400)
        vis = MovementVisualizer(network)
        vis.visualize()   # scrub with slider
        vis.animate()     # auto-play
    """

    def __init__(
        self,
        network: Network,
        logger: Optional[EdgeLogger] = None,
    ):
        self.network = network
        self.logger = logger if logger is not None else EdgeLogger()

    # ------------------------------------------------------------------
    # Public visualisation methods
    # ------------------------------------------------------------------

    def animate(
        self,
        n_frames: int = 300,
        interval_ms: int = 50,
        show_routes: bool = False,
    ) -> None:
        """Render an auto-playing animation of all entity movements.

        The movement window (first entry to last exit) is compressed to
        ``n_frames * interval_ms`` milliseconds of wall time.

        Args:
            n_frames: Number of animation frames (default 300).
            interval_ms: Milliseconds between frames (default 50 → 20 fps).
            show_routes: If True, draw semi-transparent route lines showing
                each entity's full trajectory through the network.
        """
        import matplotlib.pyplot as plt
        import matplotlib.animation as anim

        segments, node_pos, frame_times = self._prepare(n_frames)
        if segments is None:
            return

        fig, ax = plt.subplots(figsize=(12, 9))
        
        # Draw routes first (behind network and markers) if requested
        if show_routes:
            self._draw_routes(ax, segments, node_pos)
        
        markers = self._draw_network_and_markers(ax, segments, node_pos, frame_times[0])
        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        plt.tight_layout()

        def _update(frame_idx: int) -> None:
            t = frame_times[frame_idx]
            for eid, sc in markers.items():
                x, y = self._position_at(segments[eid], t, node_pos)
                sc.set_offsets([[x, y]])
            fig.suptitle(f"t = {format_time(t)}", fontsize=12)

        animation = anim.FuncAnimation(
            fig, _update, frames=n_frames, interval=interval_ms, repeat=False
        )
        plt.show()

    def visualize(
        self,
        n_steps: int = 300,
        show_routes: bool = False,
    ) -> None:
        """Render an interactive slider view of all entity movements.

        A slider beneath the plot lets you scrub freely through the movement
        window. Moving the slider updates all entity positions immediately.

        Args:
            n_steps: Number of discrete time steps the slider snaps to
                (default 300).
            show_routes: If True, draw semi-transparent route lines showing
                each entity's trajectory as it's traversed (builds up over time).
        """
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider

        segments, node_pos, frame_times = self._prepare(n_steps)
        if segments is None:
            return

        fig, ax = plt.subplots(figsize=(12, 9))
        plt.subplots_adjust(bottom=0.12)

        # Create route lines that will be progressively shown if requested
        route_lines = {}
        if show_routes:
            route_lines = self._create_route_lines(ax, segments, node_pos)

        markers = self._draw_network_and_markers(ax, segments, node_pos, frame_times[0])
        title = fig.suptitle(f"t = {format_time(frame_times[0])}", fontsize=12)
        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")

        slider_ax = fig.add_axes([0.15, 0.04, 0.7, 0.03])
        slider = Slider(
            slider_ax, "Time step",
            0, n_steps - 1,
            valinit=0, valstep=1,
        )

        def _update(val: float) -> None:
            t = frame_times[int(val)]
            
            # Update marker positions
            for eid, sc in markers.items():
                x, y = self._position_at(segments[eid], t, node_pos)
                sc.set_offsets([[x, y]])
            
            # Update route visibility - show only segments traversed up to time t
            if show_routes:
                for eid, lines in route_lines.items():
                    entity_segments = segments[eid]
                    for i, line in enumerate(lines):
                        if i < len(entity_segments):
                            t_entry, t_exit, _, _ = entity_segments[i]
                            # Show segment if we've passed its exit time
                            line.set_visible(t >= t_exit)
            
            title.set_text(f"t = {format_time(t)}")
            fig.canvas.draw_idle()

        slider.on_changed(_update)
        plt.show()

    # ------------------------------------------------------------------
    # Shared setup helpers
    # ------------------------------------------------------------------

    def _prepare(
        self, n_steps: int
    ) -> Tuple[
        Optional[Dict[str, List[_Segment]]],
        Dict[int, Tuple[float, float]],
        List[float],
    ]:
        """Parse log data and build frame times.

        Returns:
            Tuple of ``(segments, node_pos, frame_times)``.
            ``segments`` is ``None`` when there is no data to display.
        """
        segments = self._build_segments()
        if not segments:
            print("MovementVisualizer: no movement data to display.")
            return None, {}, []

        node_pos: Dict[int, Tuple[float, float]] = {
            nid: (node.x, node.y) for nid, node in self.network.nodes.items()
        }

        all_times = [
            t
            for segs in segments.values()
            for t_entry, t_exit, _, _ in segs
            for t in (t_entry, t_exit)
        ]
        t_min, t_max = min(all_times), max(all_times)
        duration = t_max - t_min or 1.0
        frame_times = [
            t_min + duration * i / max(n_steps - 1, 1) for i in range(n_steps)
        ]

        return segments, node_pos, frame_times

    def _draw_network_and_markers(
        self,
        ax,
        segments: Dict[str, List[_Segment]],
        node_pos: Dict[int, Tuple[float, float]],
        t_init: float,
    ) -> Dict[str, object]:
        """Draw the static network background and place initial entity markers.

        Args:
            ax: The matplotlib axes to draw on.
            segments: Per-entity movement segments.
            node_pos: Mapping from node_id to (x, y).
            t_init: Simulation time at which to place markers initially.

        Returns:
            Mapping from entity_id to its scatter artist.
        """
        import matplotlib.pyplot as plt

        # Static network — same style as Network.visualize()
        for edge in self.network.edges.values():
            src = self.network.nodes[edge.from_node]
            dst = self.network.nodes[edge.to_node]
            ax.annotate(
                "",
                xy=(dst.x, dst.y),
                xytext=(src.x, src.y),
                arrowprops=dict(
                    arrowstyle="->",
                    color="lightgray",
                    lw=1.0,
                    shrinkA=12,
                    shrinkB=12,
                ),
            )
        for node in self.network.nodes.values():
            ax.scatter(node.x, node.y, s=150, color="steelblue", zorder=5)
            ax.text(
                node.x, node.y, str(node.node_id),
                fontsize=2, ha="center", va="center",
                color="white", fontweight="bold", zorder=6,
            )

        # Entity markers — shape by courier, color by vehicle
        entity_ids = sorted(segments.keys())
        cmap = plt.cm.tab10
        markers = {}
        for i, eid in enumerate(entity_ids):
            x0, y0 = self._position_at(segments[eid], t_init, node_pos)
            shape = _get_entity_shape(eid)
            sc = ax.scatter(
                [x0], [y0],
                s=200,
                color=cmap(i % 10),
                marker=shape,
                edgecolors="white",
                linewidths=1.5,
                zorder=7,
                label=eid,
            )
            markers[eid] = sc

        ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
        return markers

    def _draw_routes(
        self,
        ax,
        segments: Dict[str, List[_Segment]],
        node_pos: Dict[int, Tuple[float, float]],
    ) -> None:
        """Draw semi-transparent route lines for each entity.

        Connects all traversed edges in order to show the full path
        taken by each entity through the network.

        Args:
            ax: The matplotlib axes to draw on.
            segments: Per-entity movement segments.
            node_pos: Mapping from node_id to (x, y).
        """
        import matplotlib.pyplot as plt

        entity_ids = sorted(segments.keys())
        cmap = plt.cm.tab10

        for i, eid in enumerate(entity_ids):
            color = cmap(i % 10)
            entity_segments = segments[eid]

            # Draw lines for each traversed edge
            for t_entry, t_exit, from_node, to_node in entity_segments:
                if from_node in node_pos and to_node in node_pos:
                    x1, y1 = node_pos[from_node]
                    x2, y2 = node_pos[to_node]
                    ax.plot(
                        [x1, x2],
                        [y1, y2],
                        color=color,
                        alpha=0.95,
                        linewidth=3.5,
                        zorder=1,
                    )

    def _create_route_lines(
        self,
        ax,
        segments: Dict[str, List[_Segment]],
        node_pos: Dict[int, Tuple[float, float]],
    ) -> Dict[str, List]:
        """Create route line objects for progressive display.

        Creates line objects for each traversed edge that can be
        shown/hidden dynamically based on current time.

        Args:
            ax: The matplotlib axes to draw on.
            segments: Per-entity movement segments.
            node_pos: Mapping from node_id to (x, y).

        Returns:
            Dictionary mapping entity_id to list of line artists.
        """
        import matplotlib.pyplot as plt

        entity_ids = sorted(segments.keys())
        cmap = plt.cm.tab10
        route_lines = {}

        for i, eid in enumerate(entity_ids):
            color = cmap(i % 10)
            entity_segments = segments[eid]
            lines = []

            # Create line objects for each traversed edge (initially hidden)
            for t_entry, t_exit, from_node, to_node in entity_segments:
                if from_node in node_pos and to_node in node_pos:
                    x1, y1 = node_pos[from_node]
                    x2, y2 = node_pos[to_node]
                    (line,) = ax.plot(
                        [x1, x2],
                        [y1, y2],
                        color=color,
                        alpha=0.95,
                        linewidth=3.5,
                        zorder=1,
                        visible=False,  # Initially hidden
                    )
                    lines.append(line)
            
            route_lines[eid] = lines

        return route_lines

    # ------------------------------------------------------------------
    # Log parsing and position interpolation
    # ------------------------------------------------------------------

    def _build_segments(self) -> Dict[str, List[_Segment]]:
        """Parse the edge log into per-entity movement segments.

        Returns:
            Mapping from entity_id to a time-ordered list of
            ``(t_entry, t_exit, from_node, to_node)`` tuples.
        """
        pending: Dict[str, Tuple[float, int, int]] = {}
        segments: Dict[str, List[_Segment]] = {}

        for line in self.logger.entries:
            parts = [p.strip() for p in line.split(",")]
            time = float(parts[0])
            entity_id = parts[2]
            action = parts[3]
            from_node = int(parts[4])
            to_node = int(parts[5])

            if entity_id not in segments:
                segments[entity_id] = []

            if action == "entry":
                pending[entity_id] = (time, from_node, to_node)
            elif action == "exit" and entity_id in pending:
                t_entry, fn, tn = pending.pop(entity_id)
                segments[entity_id].append((t_entry, time, fn, tn))

        for eid in segments:
            segments[eid].sort(key=lambda s: s[0])

        return segments

    @staticmethod
    def _position_at(
        entity_segments: List[_Segment],
        time: float,
        node_pos: Dict[int, Tuple[float, float]],
    ) -> Tuple[float, float]:
        """Return the interpolated (x, y) position of an entity at *time*.

        Before the first segment the entity sits at its departure node.
        After the last segment it rests at its final arrival node.
        During a segment the position is linearly interpolated.

        Args:
            entity_segments: Time-ordered list of movement segments.
            time: Query time in simulation seconds.
            node_pos: Mapping from node_id to (x, y).

        Returns:
            Interpolated (x, y) position.
        """
        last_node: Optional[int] = None

        for t_entry, t_exit, fn, tn in entity_segments:
            if time < t_entry:
                return node_pos[fn] if last_node is None else node_pos[last_node]
            if t_entry <= time <= t_exit:
                alpha = (time - t_entry) / (t_exit - t_entry) if t_exit > t_entry else 0.0
                fx, fy = node_pos[fn]
                tx, ty = node_pos[tn]
                return fx + (tx - fx) * alpha, fy + (ty - fy) * alpha
            last_node = tn

        if last_node is not None:
            return node_pos[last_node]
        if entity_segments:
            return node_pos[entity_segments[0][2]]
        return 0.0, 0.0
