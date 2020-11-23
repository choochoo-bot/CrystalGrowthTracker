## -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 15:45:07 2020

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

@copyright 2020
@author: j.h.pickering@leeds.ac.uk and j.leng@leeds.ac.uk
"""
# set up linting conditions
# pylint: disable = too-many-public-methods
# pylint: disable = c-extension-no-member

import sys
import os
import datetime
sys.path.insert(0, '..\\CrystalGrowthTracker')

from cgt.util.utils import find_hostname_and_ip

import array as arr
import numpy as np

from imageio import get_reader as imio_get_reader

from cgt.model.videoanalysisresultsstore import VideoAnalysisResultsStore

import PyQt5.QtWidgets as qw
import PyQt5.QtGui as qg
import PyQt5.QtCore as qc

from shutil import copy2

from cgt.gui import ImageLabel
from cgt.gui.projectstartdialog import ProjectStartDialog
from cgt.gui.projectpropertieswidget import ProjectPropertiesWidget

from cgt.gui.regionselectionwidget import RegionSelectionWidget
from cgt.gui.crystaldrawingwidget import CrystalDrawingWidget
from cgt.gui.videoparametersdialog import VideoParametersDialog
from cgt.gui.reportviewwidget import ReportViewWidget

from cgt.io import htmlreport
from cgt.io import writecsvreports
from cgt.io import readcsvreports

from cgt.model.cgtproject import CGTProject

# import UI
from cgt.gui.Ui_CrystalGrowthTrackerMain import Ui_CrystalGrowthTrackerMain

class CrystalGrowthTrackerMain(qw.QMainWindow, Ui_CrystalGrowthTrackerMain):
    """
    The implementation of the GUI, all the functions and
    data-structures required to implement the intended behaviour
    """

    def __init__(self, parent=None):
        """
        the object initalization function

            Args:
                parent (QObject): the parent QObject for this window

            Returns:
                None
        """
        super(CrystalGrowthTrackerMain, self).__init__(parent)
        ## the parent object
        self._parent = parent

        ## the name in the current translation
        self._translated_name = self.tr("CrystalGrowthTracker")

        self.setupUi(self)

        ## the name of the project
        self._project_name = None

        ## a pointer for the video file reader
        self._video_reader = None

        ## the project data structure
        self._project = None


        ## base widget for properties tab
        self._propertiesTab = qw.QWidget(self)

        ## the region selection widget
        self._propertiesWidget = ProjectPropertiesWidget(self._propertiesTab, self)

        # set up tab
        self.add_tab(self._propertiesTab, self._propertiesWidget, "Project Properties")


        ## base widget for region selection tab
        self._selectTab = qw.QWidget(self)

        ## the region selection widget
        self._selectWidget = RegionSelectionWidget(self._selectTab, self)

        # set up tab
        self.add_tab(self._selectTab, self._selectWidget, "Select Regions")


        ## base widget of crystal drawing tab
        self._drawingTab = qw.QWidget(self)

        ## the crystal drawing widget
        self._drawingWidget = CrystalDrawingWidget(self._drawingTab, self)

        # set up tab
        self.add_tab(self._drawingTab, self._drawingWidget, "Trace Crystals")


        ## base widget for results tab
        self._resultsTab = qw.QWidget(self)

        ## the results widget
        self._resultsWidget = None #ResultsDisplayWidget(self._selectTab, self)

        # set up tab
        self.add_tab(self._resultsTab, self._resultsWidget, "Results Overview")


        ## base widget for Report tab
        self._reportTab = qw.QWidget(self)

        ## the report widget
        self._reportWidget = ReportViewWidget(self._selectTab, self)
        self._reportWidget.set_html("<!DOCTYPE html><html><body><h1 style=\"color:blue;\">No Report!</h1><p style=\"color:red;\">No report has been saved.</p></body></html>")

        # set up tab
        self.add_tab(self._reportTab, self._reportWidget, "Current Report")


        # set up the title
        self.set_title()

    def add_tab(self, tab_widget, target_widget, title):
        """
        add a new tab

            Args:
                tab_widget (QWidget) the widget forming the tab
                target_widget (QWidget subclass) the widget to be used
                title (string) the tabbox title

            Returns:
                None
        """
        if target_widget is not None:
            layout = qw.QVBoxLayout()
            layout.addWidget(target_widget)
            tab_widget.setLayout(layout)

        self._tabWidget.addTab(tab_widget, title)

    def display_properties(self):
        """
        display the properties tab with the current properties

            Returns:
                None
        """
        self._propertiesWidget.clear_and_display_text("<h1>Properties</h1>")
        for key in self._project:
            text = "<p><b>{}:</b> {}"
            text = text.format(key, self._project[key])
            self._propertiesWidget.append_text(text)

        self._propertiesWidget.show_top_text()

        self._tabWidget.setCurrentWidget(self._propertiesTab)

    @qc.pyqtSlot()
    def new_project(self):
        """
        callback for starting a new project

            Returns:
                None
        """
        if self._project is not None:
            mb_reply = qw.QMessageBox.question(
                self,
                self.tr('CrystalGrowthTracker'),
                self.tr('You have a project that will be overwriten. Proceed?'),
                qw.QMessageBox.Yes | qw.QMessageBox.No,
                qw.QMessageBox.No)

            if mb_reply == qw.QMessageBox.No:
                return

        dia = ProjectStartDialog(self)
        dia.show()

    @qc.pyqtSlot()
    def load_project(self):
        """
        callback for loading an existing project
            Returns:
                None
        """
        print("CrystalGrowthTrackerMain.load_project()")

        if self._project is not None:
            mb_reply = qw.QMessageBox.question(
                self,
                self.tr('CrystalGrowthTracker'),
                self.tr('You have a project loaded that will be lost when you load. Proceed?'),
                qw.QMessageBox.Yes | qw.QMessageBox.No,
                qw.QMessageBox.No)

            if mb_reply == qw.QMessageBox.No:
                return

        dir_name = qw.QFileDialog.getExistingDirectory(
            self,
            self.tr("Select the Project Directory."),
            os.path.expanduser('~'))

        if dir_name != '':
            project = CGTProject()
            error_code = readcsvreports.read_csv_project(dir_name, project)
            if error_code != 0:
                message = "The project could not be loaded"
                qw.QMessageBox.warning(self,
                                       "CGT Error Loading Projcet",
                                       message)
                return

            self._project = project
            self._project.reset_changed()
            self.project_created_or_loaded()

    def project_created_or_loaded(self):
        """
        carry out action for a newly created or loaded project

            Returns:
                None
        """
        self.reset_tab_wigets()

        # remove old reader
        self._video_reader = None

        # dispaly project
        self.display_properties()
        self.set_title()

        # if project has regions
        if self._project["results"] is not None:
            if self._project["results"].number_of_regions > 0:
                self._selectWidget.reload_combobox()
                self._drawingWidget.new_region()

        self._selectWidget.setEnabled(False)
        self._drawingWidget.setEnabled(False)

        if self._project["latest_report"] is not None:
            if self._project["latest_report"] != "":
                self._reportWidget.read_report(self._project["latest_report"])

    def reset_tab_wigets(self):
        """
        reset the tab widgets to inital conditions

            Returns:
                None
        """
        self._drawingWidget.clear()
        self._selectWidget.clear()
        self._propertiesWidget.clear()
        self._reportWidget.clear()
        #self._resultsWidget.clear()

    @qc.pyqtSlot()
    def save_project(self):
        '''
        Function to write all the csv files needed to define a project.
        Args:
            self    Needs to access the project dictionary.
        Returns:
            None
        '''
        if self._project is None:
            qw.QMessageBox.warning(self,
                                   "CGT Error",
                                   "You do not have a project to save!")
            return

        try:
            writecsvreports.save_csv_project(self._project)
            self._project.reset_changed()
        except OSError as err:
            message = "Error opening writing file: {}".format(err)
            print(message)
            for item in sys.exc_info():
                print("{}".item)
            qw.QMessageBox.warning(self, "CGT File Error", message)
            return

        message = "Project saved to: {}".format(self._project["proj_full_path"])
        qw.QMessageBox.information(self, "CGT File", message)

    @qc.pyqtSlot()
    def save_report(self):
        """
        generate and save a report of the current state of the project

            Returns:
                None
        """
        if self._project is None:
            qw.QMessageBox.warning(self,
                                   "CGT Error",
                                   "You do not have a project to report!")
            return

        if self._project["proj_full_path"] is not None:
            time_stamp = utils.timestamp()
            try:
                self._project["latest_report"] = htmlreport.save_html_report1(self._project, time_stamp)
            except OSError as err:
                message = "Problem creating report directory and file: {}".format(err)
                qw.QMessageBox.warning(self,
                                       "Report Error",
                                       message)

            # read back in to the reports tab
            try:
                self._reportWidget.read_report(self._project["latest_report"])
            except OSError as err:
                message = "Could not open report file for reading: {}".format(err)
                qw.QMessageBox.warning(self,
                                       "Report Error",
                                       message)

    def start_project(self,
                      enhanced_video,
                      raw_video,
                      proj_dir,
                      proj_name,
                      notes,
                      copy_files):
        """
        function for starting a new project

            Args
                enhanced_video (pathlib.Path) the video on which the program will run
                raw_video (pathlib.Path) secondary raw_video video
                proj_dir  (pathlib.Path) parent directory of project directory
                proj_name (string) the name of project, will be directory name
                notes (string) project notes
                copy_files (bool) if true the enhanced_video and raw_video files are copied to project dir

            Returns:
                None
        """
        # make the full project path
        path = proj_dir.joinpath(proj_name)

        if path.exists():
            message = "Project {} already exists you are not allowd to overwrite.".format(proj_name)
            qw.QMessageBox.critical(self, "Project Exists!", message)
            return

        self._project = CGTProject()
        self._project.init_new_project()

        try:
            path.mkdir()
        except (FileNotFoundError, OSError) as err:
            message = "Error making project directory \"{}\"".format(err)
            qw.QMessageBox.critical(self, "Cannot Create Project!", message)
            return

        self._project["proj_name"] = proj_name
        self._project["proj_full_path"] = path

        if copy_files:
            try:
                copy2(enhanced_video, path)
                # if copied enhanced_video is project path + file name
                self._project["enhanced_video"] = path.joinpath(enhanced_video.name)

            except (IOError, os.error) as why:
                qw.QMessageBox.warning(
                    self,
                    "Problem copying File",
                    "Error message: {}".format(why))
            except Error as err:
                qw.QMessageBox.warning(
                    self,
                    "Problem copying File",
                    "Error message: {}".format(err.args[0]))

            if raw_video is not None:
                try:
                    copy2(raw_video, path)
                    # if used and copied raw_video is project path + file name
                    self._project["raw_video"] = path.joinpath(raw_video.name)
                except (IOError, os.error) as why:
                    qw.QMessageBox.warning(
                        self,
                        "Problem copying File",
                        "Error message: {}".format(why))
                except Error as err:
                    qw.QMessageBox.warning(
                        self,
                        "Problem copying File",
                        "Error message: {}".format(err.args[0]))
        else:
            # set sourec and project to their user input values
            self._project["enhanced_video"] = enhanced_video
            if raw_video is not None:
                self._project["raw_video"] = raw_video

        if notes is not None and not notes.isspace() and notes:
            notes_file_name = proj_name + "_notes.txt"
            notes_file = path.joinpath(notes_file_name)
            self._project["notes"] = notes

            try:
                with open(notes_file, 'w') as n_file:
                    n_file.write(notes)
            except IOError as error:
                message = "Can't open file for the notes"
                qw.QMessageBox.critical(self, "Error making directory!", message)

        self._project['enhanced_video_path'] = enhanced_video.parent
        self._project['enhanced_video_no_path'] = enhanced_video.name
        self._project['enhanced_video_no_extension'] = enhanced_video.stem

        if raw_video is not None:
            self._project['raw_video_path'] = raw_video.parent
            self._project['raw_video_no_path'] = raw_video.name
            self._project['raw_video_no_extension'] = raw_video.stem

        self._project["results"] = VideoAnalysisResultsStore()

        self.set_video_scale_parameters()
        self.save_project()
        self.set_title()

    def set_video_scale_parameters(self):
        """
        get the video scaling parameters from the user

            Returns:
                None
        """
        if self._project['frame_rate'] is not None:
            fps = int(self._project['frame_rate'])
        else:
            fps = 8

        if self._project['resolution'] is not None:
            resolution = float(self._project['resolution'])
        else:
            resolution = 0.81

        if self._project['resolution_units'] is not None:
            units = self._project['resolution_units']
        else:
            units = VideoParametersDialog.RESOLUTION_UNITS[1]

        fps, resolution, units = VideoParametersDialog.get_values_from_user(self, fps, resolution, units)

        self._project['frame_rate'] = fps
        self._project['resolution'] = resolution
        self._project['resolution_units'] = units

        self.display_properties()

    @qc.pyqtSlot()
    def tab_changed(self):
        """
        callback for the tab widget to use when the tab is changed, put all
        state change required between the two tabs in here. the currentIndex
        function in _tabWidger will act as a state variable.

            Returns:
                None
        """
        print("tab changed")

    def get_video_reader(self):
        return self._video_reader

    def get_fps_and_resolution(self):
        """
        getter for the frames per second and the resolution of the video

            Returns:
                frames per second (int), resolution (float)
        """
        if self._project is not None:
            return int(self._project["frame_rate"]), float(self._project["resolution"])

        return None, None

    def get_result(self):
        """
        getter for the current results object

            Return:
                the current results object
        """
        if self._project:
            return self._project["results"]

        return None

    def append_region(self, region):
        """
        add a region to the results and notify the crystal drawing widget

            Args:
                region (Region) the region

            Returns:
                None
        """
        self._project["results"].add_region(region)
        self._drawingWidget.new_region()

    def set_title(self):
        """
        sets window title

            Returns:
                None
        """
        name = "No project"

        if self._project is not None and self._project["proj_name"] is not None:
            name = self._project["proj_name"]

        self.setWindowTitle(name)

    def make_pixmap(self, index, frame):
        region = self._project["results"].regions[index]

        raw = self._video_reader.get_data(frame)
        tmp = raw[region.top:region.bottom, region.left:region.right]
        img = arr.array('B', tmp.reshape(tmp.size))

        im_format = qg.QImage.Format_RGB888
        image = qg.QImage(
            img,
            region.width,
            region.height,
            3*region.width,
            im_format)

        return qg.QPixmap.fromImage(image)

    @qc.pyqtSlot()
    def load_video(self):
        """
        read in a video and display

            Returns:
                None
        """
        error_title = self.tr("CGT Video File Error")
        if self._project is None:
            message = self.tr("You must load/create a project before loading video")
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return

        if self._project["enhanced_video"] is None:
            message = self.tr("The current project contains no video file")
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return

        message_box = qw.QMessageBox();
        message_box.setText("Loading Video.");
        message_box.setInformativeText("Loading video may take some time.");
        try:
            message_box.show()
            self._video_reader = imio_get_reader(self._project["enhanced_video"], 'ffmpeg')
        except (FileNotFoundError, IOError) as ex:
            message_box.close()
            message = self.tr("Unexpected error reading {}: {} => {}")
            message = meassge.format(file_name, type(ex), ex.args)
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return

        message_box.close()

        self._selectWidget.setEnabled(True)
        self._selectWidget.show_video()
        self._drawingWidget.setEnabled(True)

    @qc.pyqtSlot()
    def closeEvent(self, event):
        """
        Overrides QWidget.closeEvent
        This will be called whenever a MyApp object recieves a QCloseEvent.
        All actions required befor closing widget are here.

            Args:
                event (QEvent) the Qt event object

            Returns:
                None
        """

        message = self.tr('Do you want to leave?')
        changed = self.tr('You have unsaved data.')

        if self._project is not None and self._project.has_been_changed():
            message = changed + "\n" + message

        mb_reply = qw.QMessageBox.question(self,
                                           'CrystalGrowthTracker',
                                           message,
                                           qw.QMessageBox.Yes | qw.QMessageBox.No,
                                           qw.QMessageBox.No)

        if mb_reply == qw.QMessageBox.Yes:
            #clean-up and exit signalling

            # the event must be accepted
            event.accept()

            # to get rid tell the event-loop to schedul for deleteion
            # do not destroy as a pointer may survive in event-loop
            # which will trigger errors if it recieves a queued signal
            self.deleteLater()

        else:
            # dispose of the event in the approved way
            event.ignore()

######################################

def get_translators(lang):
    """
    find the available translations files for a languages

        Args:
        lang (string) the name of the language

        Returns:
            a list consisting of [<translator>, <system translator>]
    """
    qt_translator = qc.QTranslator()
    system_trans = qc.QTranslator()

    if lang == "German":
        if not qt_translator.load("./translation/cgt_german.qm"):
            sys.stderr.write("failed to load file cgt_german.qm")
        if not system_trans.load("qtbase_de.qm",
                                 qc.QLibraryInfo.location(qc.QLibraryInfo.TranslationsPath)):
            sys.stderr.write("failed to load file qtbase_de.qm")

    return [qt_translator, system_trans]

def select_translator():
    """
    give the user the option to choose the language other than default English

        Returns:
            if English None, else the list of translators
    """
    languages = ["English", "German"]

    lang = qw.QInputDialog.getItem(
        None, "Select Language", "Language", languages)

    if not lang[1]:
        return None

    return get_translators(lang[0])

def run_growth_tracker():
    """
    use a local function to make an isolated the QApplication object

        Returns:
            None
    """
    app = qw.QApplication(sys.argv)
    translators = select_translator()
    for translator in translators:
        qc.QCoreApplication.installTranslator(translator)

    window = CrystalGrowthTrackerMain()

    window.show()

    app.exec_()

if __name__ == "__main__":
    run_growth_tracker()