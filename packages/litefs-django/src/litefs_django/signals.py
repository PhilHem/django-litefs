"""Django signals for split-brain detection events.

Signals allow applications to react to split-brain detection events without
modifying the middleware code. Use by connecting a receiver function:

    from litefs_django.signals import split_brain_detected

    def handle_split_brain(sender, status, **kwargs):
        # status is a SplitBrainStatus object with:
        # - is_split_brain: bool
        # - leader_nodes: list[RaftNodeState]
        logger.error(f"Split brain detected: {len(status.leader_nodes)} leaders")

    split_brain_detected.connect(handle_split_brain)
"""

from django.dispatch import Signal

# Signal sent when split-brain is detected or cleared
# Provides the SplitBrainStatus object containing is_split_brain flag and leader nodes
split_brain_detected: Signal = Signal()
