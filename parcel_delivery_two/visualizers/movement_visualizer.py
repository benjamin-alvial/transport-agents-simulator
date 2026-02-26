from typing import Dict, List, Optional, Tuple

from parcel_delivery_two.environment.network import Network
from parcel_delivery_two.loggers.edge_logger import EdgeLogger
from parcel_delivery_two.utils.time_utils import format_time

# Type alias
_Segment = Tuple[float, float, int, int]  # (t_entry, t_exit, from_node, to_node)


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

    def animate(self, n_frames: int = 300, interval_ms: int = 50) -> None:
        """Render an auto-playing animation of all entity movements.

        The movement window (first entry to last exit) is compressed to
        ``n_frames * interval_ms`` milliseconds of wall time.

        Args:
            n_frames: Number of animation frames (default 300).
            interval_ms: Milliseconds between frames (default 50 → 20 fps).
        """
        import matplotlib.pyplot as plt
        import matplotlib.animation as anim

        segments, node_pos, frame_times = self._prepare(n_frames)
        if segments is None:
            return

        fig, ax = plt.subplots(figsize=(12, 9))
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

    def visualize(self, n_steps: int = 300) -> None:
        """Render an interactive slider view of all entity movements.

        A slider beneath the plot lets you scrub freely through the movement
        window. Moving the slider updates all entity positions immediately.

        Args:
            n_steps: Number of discrete time steps the slider snaps to
                (default 300).
        """
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider

        segments, node_pos, frame_times = self._prepare(n_steps)
        if segments is None:
            return

        fig, ax = plt.subplots(figsize=(12, 9))
        plt.subplots_adjust(bottom=0.12)

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
            for eid, sc in markers.items():
                x, y = self._position_at(segments[eid], t, node_pos)
                sc.set_offsets([[x, y]])
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
                    lw=1.5,
                    shrinkA=12,
                    shrinkB=12,
                ),
            )
        for node in self.network.nodes.values():
            ax.scatter(node.x, node.y, s=350, color="steelblue", zorder=5)
            ax.text(
                node.x, node.y, str(node.node_id),
                fontsize=9, ha="center", va="center",
                color="white", fontweight="bold", zorder=6,
            )

        # Entity markers — buses as triangles, vehicles as circles
        entity_ids = sorted(segments.keys())
        cmap = plt.cm.tab10
        markers = {}
        for i, eid in enumerate(entity_ids):
            x0, y0 = self._position_at(segments[eid], t_init, node_pos)
            sc = ax.scatter(
                [x0], [y0],
                s=200,
                color=cmap(i % 10),
                marker="^" if eid.startswith("bus") else "o",
                edgecolors="white",
                linewidths=1.5,
                zorder=7,
                label=eid,
            )
            markers[eid] = sc

        ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
        return markers

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
