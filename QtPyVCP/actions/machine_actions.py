#!/usr/bin/env python
# coding: utf-8

#   Copyright (c) 2018 Kurt Jacobson
#      <kurtcjacobson@gmail.com>
#
#   This file is part of QtPyVCP.
#
#   QtPyVCP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   QtPyVCP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with QtPyVCP.  If not, see <http://www.gnu.org/licenses/>.

# Description:
#   LinuxCNC coolant actions

import sys
import time
import linuxcnc
from PyQt5.QtWidgets import QAction

# Set up logging
from QtPyVCP.utilities import logger
LOG = logger.getLogger(__name__)

from QtPyVCP.utilities.status import Status, Info
from QtPyVCP.actions.base_actions import setTaskMode

STATUS = Status()
INFO = Info()
STAT = STATUS.stat
CMD = linuxcnc.command()

def bindWidget(widget, action):
    """Binds a widget to a machine action.

    Args:
        widget (QtWidget) : The widget to bind the action too. Typically `widget`
            would be a QPushButton, QCheckBox or a QAction.

        action (string) : The string identifier of the machine action to bind
            the widget to in the format `action_class.action_name:arg1, arg2 ...`.
    """
    action, sep, args = action.partition(':')
    action = action.replace('-', '_')
    method = reduce(getattr, action.split('.'), sys.modules[__name__])
    if method is None:
        return

    if isinstance(widget, QAction):
        sig = widget.triggered
    else:
        sig = widget.clicked

    if args == '':
        sig.connect(method)

    else:
        # make a list out of comma separated args
        args = args.replace(' ', '').split(',')
        # convert numbers to int and unicode to str
        args = [int(arg) if arg.isdigit() else str(arg) for arg in args]

        if action.startswith('jog'):
            widget.pressed.connect(lambda: method(*args))
            widget.released.connect(lambda: method(*args, speed=0))

        else:
            sig.connect(lambda: method(*args))

    # if it is a toggle action make the widget checkable
    if action.endswith('toggle'):
        widget.setCheckable(True)

    if action.startswith('estop'):
        STATUS.estop.connect(lambda v: widget.setChecked(not v))

    elif action.startswith('power'):
        power.ok(widget)
        STATUS.estop.connect(lambda: power.ok(widget))
        STATUS.on.connect(lambda v: widget.setChecked(v))

    elif action == 'mode.manual':
        widget.setChecked(STAT.task_mode == linuxcnc.MODE_MANUAL)
        STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_MANUAL))

    elif action == 'mode.auto':
        widget.setChecked(STAT.task_mode == linuxcnc.MODE_AUTO)
        STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_AUTO))

    elif action == 'mode.mdi':
        widget.setChecked(STAT.task_mode == linuxcnc.MODE_MDI)
        STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_MDI))

    elif action == 'home.all':
        home.ok(-1, widget)
        STATUS.on.connect(lambda: home.ok(-1, widget))
        STATUS.homed.connect(lambda: home.ok(-1, widget))

    elif action == 'home.joint':
        home.ok(arg, widget)
        STATUS.on.connect(lambda: home.ok(arg, widget))
        STATUS.homed.connect(lambda: home.ok(arg, widget))

    elif action == 'home.axis':
        axis = getAxisLetter(arg)
        jnum = INFO.AXIS_LETTER_LIST.index(arg.lower())
        home.ok(arg, widget)
        STATUS.on.connect(lambda: home.ok(jnum, widget))

    elif action.startswith('jog'):
        pass

# -------------------------------------------------------------------------
# E-STOP action
# -------------------------------------------------------------------------
class estop:
    """E-Stop action group"""
    @staticmethod
    def activate():
        """Set E-Stop active"""
        LOG.debug("Setting state red<ESTOP>")
        CMD.state(linuxcnc.STATE_ESTOP)

    @staticmethod
    def reset():
        """Resets E-Stop"""
        LOG.debug("Setting state green<ESTOP_RESET>")
        CMD.state(linuxcnc.STATE_ESTOP_RESET)

    @staticmethod
    def toggle():
        """Toggles E-Stop state"""
        if estop.is_activated():
            estop.reset()
        else:
            estop.activate()

    @staticmethod
    def is_activated():
        """Checks if E_Stop is activated.

        Returns:
            bool : True if E-Stop is active, else False.
        """
        return bool(STAT.estop)

def _estop_ok(widget=None):
    # E-Stop is ALWAYS ok, but provide this method for consistency
    _estop_ok.msg = ""
    return True

def _estop_bindOk(widget):
    widget.setChecked(STAT.estop != linuxcnc.STATE_ESTOP)
    STATUS.estop.connect(lambda v: widget.setChecked(not v))

estop.activate.ok = estop.reset.ok = estop.toggle.ok = _estop_ok
estop.activate.bindOk = estop.reset.bindOk = estop.toggle.bindOk = _estop_bindOk

# -------------------------------------------------------------------------
# POWER action
# -------------------------------------------------------------------------
class power:
    """Power action group"""
    @staticmethod
    def on():
        """Turns machine power On"""
        LOG.debug("Setting state green<ON>")
        CMD.state(linuxcnc.STATE_ON)

    @staticmethod
    def off():
        """Turns machine power Off"""
        LOG.debug("Setting state red<OFF>")
        CMD.state(linuxcnc.STATE_OFF)

    @staticmethod
    def toggle():
        """Toggles machine power On/Off"""
        if power.is_on():
            power.off()
        else:
            power.on()

    @staticmethod
    def is_on():
        """Checks if power is on.

        Returns:
            bool : True if power is on, else False.
        """
        return STAT.task_state == linuxcnc.STATE_ON

def _power_ok(widget=None):
    if STAT.task_state == linuxcnc.STATE_ESTOP_RESET:
        ok = True
        msg = ""
    else:
        ok = False
        msg = "Can't turn machine ON until out of E-Stop"

    _power_ok.msg = msg

    if widget is not None:
        widget.setEnabled(ok)
        widget.setStatusTip(msg)
        widget.setToolTip(msg)

    return ok

def _power_bindOk(widget):
    _power_ok(widget)
    widget.setChecked(STAT.task_state == linuxcnc.STATE_ON)
    STATUS.estop.connect(lambda: _power_ok(widget))
    STATUS.on.connect(lambda v: widget.setChecked(v))

power.on.ok = power.off.ok = power.toggle.ok = _power_ok
power.on.bindOk = power.off.bindOk = power.toggle.bindOk = _power_bindOk

# -------------------------------------------------------------------------
# FEED HOLD action
# -------------------------------------------------------------------------
class feedhold:

    # FIXME For some reason these do not work

    @staticmethod
    def on():
        print "FeedHold ON"
        CMD.set_feed_hold(1)

    @staticmethod
    def off():
        print "FeedHold OFF"
        CMD.set_feed_hold(0)

    @staticmethod
    def toggle():
        print "FeedHold TOGGLE"
        print STAT.feed_hold_enabled
        if STAT.feed_hold_enabled:
            feedhold.off()
        else:
            feedhold.on()


# -------------------------------------------------------------------------
# set MODE actions
# -------------------------------------------------------------------------
class mode:
    @staticmethod
    def manual():
        setTaskMode(linuxcnc.MODE_MANUAL)

    @staticmethod
    def auto():
        setTaskMode(linuxcnc.MODE_AUTO)

    @staticmethod
    def mdi():
        setTaskMode(linuxcnc.MODE_MDI)

def _mode_ok(widget=None):

    ok = True
    msg = ''

    _mode_ok.msg = msg

    if widget is not None:
        widget.setEnabled(ok)
        widget.setStatusTip(msg)
        widget.setToolTip(msg)

    return ok

def _manual_bindOk(widget):
    widget.setChecked(STAT.task_mode == linuxcnc.MODE_MANUAL)
    STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_MANUAL))

mode.manual.ok = _mode_ok
mode.manual.bindOk = _manual_bindOk

def _auto_bindOk(widget):
    widget.setChecked(STAT.task_mode == linuxcnc.MODE_AUTO)
    STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_AUTO))

mode.auto.ok = _mode_ok
mode.auto.bindOk = _auto_bindOk

def _mdi_bindOk(widget):
    widget.setChecked(STAT.task_mode == linuxcnc.MODE_MDI)
    STATUS.task_mode.connect(lambda m: widget.setChecked(m == linuxcnc.MODE_MDI))

mode.mdi.ok = _mode_ok
mode.mdi.bindOk = _mdi_bindOk

# -------------------------------------------------------------------------
# HOME actions
# -------------------------------------------------------------------------
class home:
    """Homing actions group"""
    @staticmethod
    def all():
        """Homes all axes."""
        LOG.info("Homing all axes")
        _home_joint(-1)

    @staticmethod
    def axis(axis):
        """Home a specific axis.

        Args:
            axis (int | str) : Either the axis letter or number to home.
        """
        axis = getAxisLetter(axis)
        if axis.lower() == 'all':
            home.all()
            return
        jnum = INFO.COORDINATES.index(axis)
        LOG.info('Homing Axis: {}'.format(axis.upper()))
        _home_joint(jnum)

    @staticmethod
    def joint(jnum):
        """Home a specific joint.

        Args:
            jnum (int) : The number of the joint to home.
        """
        LOG.info("Homing joint: {}".format(jnum))
        _home_joint(jnum)

def _home_ok(widget=None, jnum=-1):
    if power.is_on(): # and not STAT.homed[jnum]:
        ok = True
        msg = ""
    else:
        ok = False
        msg = "Machine must be on to home"

    _home_ok.msg = msg

    if widget is not None:
        widget.setEnabled(ok)
        widget.setStatusTip(msg)
        widget.setToolTip(msg)

    return ok

def _home_all_bindOk(widget):
    STATUS.on.connect(lambda: _home_ok(widget))
    STATUS.homed.connect(lambda: _home_ok(widget))

home.all.ok = _home_ok
home.all.bindOk = _home_all_bindOk

def _home_joint_bindOk(widget, jnum):
    STATUS.on.connect(lambda: _home_ok(widget, jnum))
    STATUS.homed.connect(lambda: _home_ok(widget, jnum))

home.joint.ok = _home_ok
home.joint.bindOk = _home_joint_bindOk

def _home_axis_bindOk(widget, axis):
    axis = getAxisLetter(axis)
    jnum = INFO.AXIS_LETTER_LIST.index(axis)
    STATUS.on.connect(lambda: _home_ok(widget, jnum))

home.axis.ok = _home_ok
home.axis.bindOk = _home_axis_bindOk


class unhome:
    """Unhoming actions group"""
    @staticmethod
    def all():
        pass

    @staticmethod
    def axis(axis):
        pass

    @staticmethod
    def joint(jnum):
        pass

def _home_joint(jnum):
    setTaskMode(linuxcnc.MODE_MANUAL)
    CMD.teleop_enable(False)
    CMD.home(jnum)

def _unhome_joint(jnum):
    setTaskMode(linuxcnc.MODE_MANUAL)
    CMD.teleop_enable(False)
    CMD.home(jnum)

# Homing helper functions

def getAxisLetter(axis):
    """Takes an axis letter or number and returns the axis letter.

    Args:
        axis (int | str) : Either a axis letter or an axis number.

    Returns:
        str : The axis letter, `all` for an input of -1.
    """
    if isinstance(axis, int):
        return ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w', 'all'][axis]
    return axis.lower()

def getAxisNumber(axis):
    """Takes an axis letter or number and returns the axis number.

    Args:
        axis (int | str) : Either a axis letter or an axis number.

    Returns:
        int : The axis number, -1 for an input of `all`.
    """
    if isinstance(axis, str):
        return ['x', 'y', 'z', 'a', 'b', 'c', 'u', 'v', 'w', 'all'].index(axis.lower())
    return axis


class jog:
    @staticmethod
    def axis(axis, direction=0, speed=None, distance=None):
        """Jog an axis.

        Args:
            axis (str | int) : Either the letter or number of the axis to jog.
            direction (str | int) : pos or +1 for positive, neg or -1 for negative.
            speed (float, optional) : Desired jog vel in machine_units/s.
            distance (float, optional) : Desired jog distance, continuous jog if 0.00.
        """

        if isinstance(direction, str):
            direction = {'neg': -1, 'pos': 1}.get(direction.lower(), 0)

        axis = getAxisNumber(axis)

        if speed == 0 or direction == 0:
            CMD.jog(linuxcnc.JOG_STOP, 0, axis)

        else:

            if speed is None:
                if axis in (3,4,5):
                    speed = STATUS.angular_jog_velocity / 60
                else:
                    speed = STATUS.linear_jog_velocity / 60

            if distance is None:
                distance = STATUS.jog_increment

            velocity = float(speed) * direction

            if distance == 0:
                CMD.jog(linuxcnc.JOG_CONTINUOUS, 0, axis, velocity)
            else:
                CMD.jog(linuxcnc.JOG_INCREMENT, 0, axis, velocity, distance)
