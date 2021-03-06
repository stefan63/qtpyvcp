"""
VCP Frame
---------

A frame widget that can be controlled via rules.
"""

from qtpy.QtWidgets import QFrame
from qtpyvcp.widgets.base_widgets import VCPWidget


class VCPFrame(QFrame, VCPWidget):
    """VCPFrame"""

    DEFAULT_RULE_PROPERTY = 'Enable'

    def __init__(self, parnet):
        super(VCPFrame, self).__init__(parent=parnet)


