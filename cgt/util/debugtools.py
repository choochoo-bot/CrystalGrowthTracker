# -*- coding: utf-8 -*-
## @package debugtools
# functions converting qt internals to strings for printing in logs or debuging
#
# @copyright 2021 University of Leeds, Leeds, UK.
# @author j.h.pickering@leeds.ac.uk and j.leng@leeds.ac.uk
"""
Created on Wed June 16 2021

This module contains the top level graphical user interface for measuring the
growth rates of crystals observed in videos taken using an X-ray synchrotron source

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

This work was funded by Joanna Leng's EPSRC funded RSE Fellowship (EP/R025819/1)
"""

def qtransform_to_string(trans):
    """
    convert a qt transform (3x3 matrix) to string
        Args:
            trans (Qt.Transform) the transform
        Returns:
            (str) text rendering of matrix
    """
    row1 = f"|{trans.m11():+.2f} {trans.m12():+.2f} {trans.m13():+.2f}|\n"
    row2 = f"|{trans.m21():+.2f} {trans.m22():+.2f} {trans.m23():+.2f}|\n"
    row3 = f"|{trans.m31():+.2f} {trans.m32():+.2f} {trans.m33():+.2f}|"
    return row1 + row2 + row3

def rectangle_to_string(rect):
    """
    convert a qt rectangle to string
        Args:
            redt (Qt.QRect) the rectangle
        Returns:
            (str) text rendering rectangle (top left corener (x,y); width; height)
    """
    top_left = rect.topLeft()
    size = rect.size()
    return f"QRect({top_left.x()}, {top_left.y()}) ({size.width()}, {size.height()})"
