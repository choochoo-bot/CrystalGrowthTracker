# -*- coding: utf-8 -*-
"""
Created on Wed Jun 10 11:28:23 2020

provides a class, derived from QLabel, that allows the user to select a
retcangular region of a pixmap in pixmap coordinates

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

@copyright 2020
@author: j.h.pickering@leeds.ac.uk
"""
from enum import IntEnum
import PyQt5.QtWidgets as qw
import PyQt5.QtGui as qg
import PyQt5.QtCore as qc
import numpy as np

from DrawRect import DrawRect

import lazylogger

# set up linting conditions
# pylint: disable = too-many-public-methods
# pylint: disable = c-extension-no-member

class SelectionState(IntEnum):
    """
    the current activity
    """

    ## simply work as a label
    NO_ACTION = 10

    ## the user is going to enter a new region
    ADD_NEW_REGION = 20

    ## Display one region
    DISPLAY_SELECTED = 30

    ## Display all regions
    DISPLAY_ALL = 40

    ## Display all time independent
    DISPLAY_ALL_NO_TIME = 50


class RegionSelectionLabel(qw.QLabel):
    """
    subclass of label allowing selection of region by drawing rectangle and
    displaying a list of already selected rectangles.
    """
    def __init__(self, parent=None):
        """
        Set up the label

            Args:
                parent (QObject) the parent object

            Returns:
                None
        """
        super(qw.QLabel, self).__init__()

        ## (QObject) the parent object
        self._parent = parent

        ## the widget's state
        self._state = SelectionState.NO_ACTION

        ## the translated name
        self._translation_name = self.tr("ImageLabel")

        ## holder for start of drawing in pixel coordinates
        self._start = None

        ## holder for end of drawing in pixel coordinates
        self._end = None

        ## holder for the rectangle which a user has defined, but not yet formed a region
        self._rectangle = None

        ## the logger
        self._logger = lazylogger.logging.getLogger(self._translation_name)
        self._logger.setLevel(lazylogger.logging.WARNING)

    ## signal to indicate the user has selected a new rectangle
    new_selection = qc.pyqtSignal()
    
    @property
    def rectangle(self):
        """
        getter for the rectangle
        
            Returns:
                the user's current rectangle or None
        """
        return self._rectangle

    def set_no_action(self):
        """
        set the state to

            Returns:
                None
        """
        self._state = SelectionState.NO_ACTION

    def set_adding(self):
        """
        set the state to

            Returns:
                None
        """
        self._state = SelectionState.ADD_NEW_REGION

    def set_display_selected(self, index):
        """
        set the state to

            Args:
                index (int) the list index of the region to be displayed

            Returns:
                None
        """
        self._state = SelectionState.DISPLAY_SELECTED

    def set_display_all(self):
        """
        set the state to

            Returns:
                None
        """
        self._state = SelectionState.DISPLAY_ALL

    def set_display_all_no_time(self):
        """
        set the state to

            Returns:
                None
        """
        self._state = SelectionState.DISPLAY_ALL_NO_TIME

    def mousePressEvent(self, event):
        """
        detect the start of selection

            Args:
                event (QEvent) the event data

            Returns:
                None
        """
        if event.button() == qc.Qt.LeftButton:
            if self._state ==  SelectionState.ADD_NEW_REGION:
                self._start = event.pos()

    def mouseMoveEvent(self, event):
        """
        If selecting draw rectangle

            Args:
                event (QEvent) the event data

            Returns:
                None
        """
        if self._start is not None:
            self._end = event.pos()
            self.repaint()

    def mouseReleaseEvent(self, event):
        """
        select rectangle

            Args:
                event (QEvent) the event data

            Returns:
                None
        """
        if event.button() == qc.Qt.LeftButton and self._state ==  SelectionState.ADD_NEW_REGION:

            self._end = event.pos()
            self.repaint()
            reply = qw.QMessageBox.question(
                self,
                self.tr("Region Selection"),
                self.tr("Do you wish to select this rectangle?"))

            if reply == qw.QMessageBox.Yes:
                self.make_rectangle()
            else:
                self.reset_selection()
                
            self.repaint()

    def reset_selection(self):
        """
        restore the selction of a new region to its initial state

            Returns:
                None
        """
        self._start = None
        self._end = None
        self._rectangle = None
        self.repaint()

    def make_rectangle(self):
        """
        add a new rectangle to the store and emit a QSignal to notify other QWidgets

            Emits:
                new_selection signal

            Returns:
                None
        """
        # get horizontal range
        horiz = (self._start.x(), self._end.x())
        zoom = self._parent.get_zoom()
        
        # get horizontal range
        start_h = np.uint32(np.round(min(horiz)/zoom))
        end_h = np.uint32(np.round(max(horiz)/zoom))

        # get vertical range
        vert = (self._start.y(), self._end.y())
        start_v = np.uint32(np.round(min(vert)/zoom))
        end_v = np.uint32(np.round(max(vert)/zoom))
        
        self._rectangle = DrawRect(start_v, end_v, start_h, end_h)
        self._start = None
        self._end = None

        self.new_selection.emit()

    def paintEvent(self, event):
        """
        if selecting than draw a rectagle

            Args:
                event (QEvent) the event data

            Returns:
                None
        """
        qw.QLabel.paintEvent(self, event)

        self.draw_rectangles()

    def draw_rectangles(self):
        """
        Draw the alreay selected rectangles and, if in selecting mode
        the current selection

            Returns:
                None
        """

        pen = qg.QPen(qg.QColor(qc.Qt.black), 1, qc.Qt.DashLine)
        brush = qg.QBrush(qg.QColor(255, 255, 255, 120))
        painter = qg.QPainter(self)
        painter.setPen(pen)
        painter.setBrush(brush)

# TODO draw parent's rectagles as required
#        for rect in self._rectangles:
#            zoomed = rect.scale(self._parent.get_zoom())
#            q_rect = qc.QRect(
#                qc.QPoint(int(zoomed.left), int(zoomed.top)),
#                qc.QPoint(int(zoomed.right), int(zoomed.bottom)))
#
#            painter.drawRect(q_rect)

        if self._start is not None and self._end is not None:
            painter.drawRect(qc.QRect(self._start, self._end))
        elif self._rectangle is not None:
            zoomed = self._rectangle.scale(self._parent.get_zoom())
            rect = qc.QRect(zoomed.left, zoomed.top, zoomed.width, zoomed.height)
            painter.drawRect(rect)
