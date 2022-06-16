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
# pylint: disable = too-many-instance-attributes
# pylint: disable = c-extension-no-member
# pylint: disable = line-too-long
# pylint: disable = invalid-name
# pylint: disable = import-error

import os
import pathlib
from shutil import copy2

import PyQt5.QtWidgets as qw
import PyQt5.QtCore as qc
import PyQt5.Qt as qt
import ffmpeg

from cgt.gui.projectstartdialog import ProjectStartDialog
from cgt.gui.projectpropertieswidget import ProjectPropertiesWidget
from cgt.gui.videoparametersdialog import VideoParametersDialog
from cgt.gui.videoregionselectionwidget import VideoRegionSelectionWidget
from cgt.gui.editnotesdialog import EditNotesDialog
from cgt.gui.markupwidget import MarkUpWidget
from cgt.gui.reportwidget import ReportWidget
from cgt.gui.videostatisticswidget import VideoStatisticsWidget
from cgt.gui.penstore import PenStore
from cgt.gui.resultswidget import ResultsWidget
from cgt.util import config

from cgt.io import (writecsvreports, readcsvreports)
from cgt.io.htmlreport import ReportMaker

from cgt.io.videosource import VideoSource
from cgt.io.videoanalyser import VideoAnalyser
from cgt.io.regionvideocopy import RegionVideoCopy

from cgt.model.cgtproject import CGTProject
from cgt.model.videoanalysisresultsstore import VideoAnalysisResultsStore

# import UI
from cgt.gui.Ui_crystalgrowthtrackermain import Ui_CrystalGrowthTrackerMain

class CrystalGrowthTrackerMain(qw.QMainWindow, Ui_CrystalGrowthTrackerMain):
    """
    The implementation of the GUI, all the functions and
    data-structures required to implement the intended behaviour
    """

    def __init__(self,
                 parent=None,
                 config_args=None):
        """
        the object initalization function
            Args:
                parent (QObject): the parent QObject for this window
                config_args (argparse.Namespace): command line initial setup arguments
        """
        super().__init__(parent)
        self.setupUi(self)

        ## the name in the current translation
        self._translated_name = self.tr("CrystalGrowthTracker")

        ## the reader for the working video
        self._enhanced_video_reader = None

        ## the reader for the raw video (if used)
        self._raw_video_reader = None

        ## the project data structure
        self._project = None

        ## the pens
        self._pens = PenStore()

        self.setup_tabs()
        self._tabWidget.setCurrentIndex(0)

        ## assign logging state
        if config_args is not None:
            args = vars(config_args)
            if args.get("log_ffmpeg") is not None and args.get("log_ffmpeg"):
                config.USE_FFMPEG_LOG = True
            if args.get("project") is not None:
                self.read_project_directory(args.get("project"))

        self._progressBar.hide()
        self.set_title()

    def setup_tabs(self):
        """
        setup the tabs
        """
        # Properties
        #############
        tab = self._tabWidget.widget(0)

        ## the properties listing widget
        self._propertiesWidget = ProjectPropertiesWidget(tab, self)
        self.setup_tab(tab, self._propertiesWidget)

        # Selection
        ############
        tab = self._tabWidget.widget(1)

        ## the region selection widget
        self._selectWidget = VideoRegionSelectionWidget(tab, self)
        self._selectWidget.setup_video_widget()
        self._selectWidget.enable(False)
        self.setup_tab(tab, self._selectWidget)

        # Video Statistics
        ###################
        tab = self._tabWidget.widget(2)

        ## the region selection widget
        self._videoStatsWidget = VideoStatisticsWidget(tab, self)
        self._videoStatsWidget.setup_video_widget()
        self._videoStatsWidget.enable(False)
        self.setup_tab(tab, self._videoStatsWidget)

        # User markup of video features
        ###############################
        tab =self._tabWidget.widget(3)

        ## the crystal drawing widget
        self._drawingWidget = MarkUpWidget(tab, self)
        self._drawingWidget.setup_video_widget()
        self._drawingWidget.setEnabled(False)
        self.setup_tab(tab, self._drawingWidget)

        # Results
        ###########
        tab = self._tabWidget.widget(4)

        ## results widget
        self._resultsWidget = ResultsWidget(tab, self)
        self.setup_tab(tab, self._resultsWidget)

        # Report results
        #################
        tab = self._tabWidget.widget(5)

        ## the report widget
        self._reportWidget = ReportWidget(tab, self)
        self.setup_tab(tab, self._reportWidget)

    def get_pens(self):
        """
        getter for the pens
            Returns:
                (PenStore)
        """
        return self._pens

    @qc.pyqtSlot(int)
    def tab_changed(self, tab_index):
        """
        callback for a change in the tabWidget
            Args:
                tab_index (int) the index of the new tab
        """
        if not self.has_project():
            return

        self._propertiesWidget.setEnabled(False)
        self._selectWidget.enable(False)
        self._videoStatsWidget.enable(False)
        self._drawingWidget.setEnabled(False)
        self._resultsWidget.setEnabled(False)
        self._reportWidget.setEnabled(False)

        if tab_index == self._tabWidget.indexOf(self._propertiesTab):
            self._propertiesTab.setEnabled(True)
        elif tab_index == self._tabWidget.indexOf(self._selectTab):
            self._selectWidget.enable(True)
            self._selectWidget.redisplay()
        elif tab_index == self._tabWidget.indexOf(self._videoStatsTab):
            if self._project["results"].get_video_statistics() is not None:
                self._videoStatsWidget.enable(True)
                self._videoStatsWidget.redisplay()
        elif tab_index == self._tabWidget.indexOf(self._drawingTab):
            self._drawingWidget.setEnabled(True)
        elif tab_index == self._tabWidget.indexOf(self._resultsTab):
            self._resultsWidget.setEnabled(True)
        elif tab_index == self._tabWidget.indexOf(self._reportTab):
            self._reportWidget.setEnabled(True)

    def has_project(self):
        """
        find if a project is loaded
            Returns:
                True if project loaded, else False
        """
        return not (self._project is None or self._enhanced_video_reader is None)

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
        if self.has_unsaved_data():
            mb_reply = qw.QMessageBox.question(
                self,
                self.tr('CrystalGrowthTracker'),
                self.tr('You have a project with unsaved data that will be lost.\nProceed?'),
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
        if self.has_unsaved_data():
            mb_reply = qw.QMessageBox.question(
                self,
                self.tr('CrystalGrowthTracker'),
                self.tr('You have a project with unsaved data that will be lost. Proceed?'),
                qw.QMessageBox.Yes | qw.QMessageBox.No,
                qw.QMessageBox.No)

            if mb_reply == qw.QMessageBox.No:
                return

        dir_name = qw.QFileDialog.getExistingDirectory(
            self,
            self.tr("Select the Project Directory."),
            os.path.expanduser('~'))

        if dir_name == '':
            return

        self.read_project_directory(dir_name)

    def read_project_directory(self, dir_name):
        """
        read a project directory
            Args:
                dir_name (string): path to the direcrory
        """
        project = CGTProject()
        project["results"] = VideoAnalysisResultsStore(self)
        project["results"].data_changed.connect(self.data_changed)
        try:
            readcsvreports.read_csv_project(dir_name, project, self.get_pens())
        except (IOError, OSError, EOFError, FileNotFoundError) as exp:
            message = f"Could not load project: {exp}"
            qw.QMessageBox.warning(self,
                                   "CGT Error Loading Project",
                                   message)
            return

        self._project = project
        self._project["results"].data_changed.connect(self.data_changed)
        self._project.reset_changed()
        self.project_created_or_loaded()

    def reset_video_widgets(self):
        """
        clear and reset the video widgets and the frame queue
        """
        self._videoStatsWidget.clear()
        self._selectWidget.clear()
        self._drawingWidget.clear()
        self._drawingWidget.set_results(self._project["results"])

    def project_created_or_loaded(self):
        """
        carry out action for a newly created or loaded project

            Returns:
                None
        """
        self.reset_tab_wigets()

        # dispaly project
        self.display_properties()
        self.set_title()
        self.load_video()
        self._selectWidget.redisplay_regions()
        self._selectWidget.display_video_file_name()
        self._drawingWidget.display_video_file_name()

        if self._project["latest_report"] is not None and self._project["latest_report"] != "":
            self._reportWidget.load_html(self._project["latest_report"])

    def reset_tab_wigets(self):
        """
        reset the tab widgets to inital conditions

            Returns:
                None
        """
        self.reset_video_widgets()
        self._propertiesWidget.clear()

    @qc.pyqtSlot()
    def save_image(self):
        """
        save an image from the currently displayed widget
        """
        # if no project, or video loaded error
        if self._project is None or self._enhanced_video_reader is None:
            message = self.tr("To save you must have a project and load a video.")
            qw.QMessageBox.information(self, self.tr("Save Image"), message)
            return

        # find if a tab holding image is in use
        current_tab_widget=self._tabWidget.currentWidget()
        widget = None

        if current_tab_widget == self._selectTab:
            widget = self._selectWidget
        elif current_tab_widget == self._drawingTab:
            widget = self._drawingWidget
        elif current_tab_widget == self._videoStatsTab:
            widget = self._videoStatsWidget
        else:
            message = self.tr("You must be using either Select Regions, Draw Crystals or Statistics tabs.")
            qw.QMessageBox.information(self, self.tr("Save Image"), message)
            return

        file_types = "Portable Network Graphics (*.png)"
        file_path, _ = qw.QFileDialog.getSaveFileName(self,
                                                     "Enter/select file for save",
                                                     os.path.expanduser('~'),
                                                     file_types)

        if file_path is None or file_path == '':
            return

        widget.save_scene(file_path)

        message = f"Image saved to {file_path}"
        qw.QMessageBox.information(self, self.tr("Save Image"), message)

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
            message = f"Error opening writing file: {err}"
            qw.QMessageBox.warning(self, "CGT File Error", message)
            return

        message = "Project saved to: {}".format(self._project["proj_full_path"])
        qw.QMessageBox.information(self, "CGT File", message)

    def start_project(self,
                      enhanced_video,
                      raw_video,
                      proj_dir,
                      proj_name,
                      notes,
                      copy_files,
                      stats_from_enhanced):
        """
        function for starting a new project
            Args
                enhanced_video (pathlib.Path) the video on which the program will run
                raw_video (pathlib.Path) secondary raw_video video
                proj_dir  (pathlib.Path) parent directory of project directory
                proj_name (string) the name of project, will be directory name
                notes (string) project notes
                copy_files (bool) if true video files are copied to project dir
                stats_from_enhanced (bool) if true & raw video included, do stats on enhanced
        """
        # make the full project path
        path = proj_dir.joinpath(proj_name)

        if path.exists():
            message = "Project {} already exists you are not allowd to overwrite.".format(proj_name)
            qw.QMessageBox.critical(self, "Project Exists!", message)
            return

        project = CGTProject()
        project.init_new_project()

        try:
            path.mkdir()
        except (FileNotFoundError, OSError) as err:
            message = "Error making project directory \"{}\"".format(err)
            qw.QMessageBox.critical(self, "Cannot Create Project!", message)
            return

        project["proj_name"] = proj_name
        project["proj_full_path"] = path

        if copy_files:
            try:
                copy2(enhanced_video, path)
                # if copied enhanced_video is project path + file name
                self._project["enhanced_video"] = path.joinpath(enhanced_video.name)

            except (IOError, os.error) as why:
                qw.QMessageBox.warning(
                    self,
                    "Problem copying video file",
                    f"Error message: {why}")

            if raw_video is not None:
                try:
                    copy2(raw_video, path)
                    # if used and copied raw_video is project path + file name
                    self._project["raw_video"] = path.joinpath(raw_video.name)
                except (IOError, os.error) as why:
                    qw.QMessageBox.warning(
                        self,
                        "Problem copying raw video file",
                        f"Error message: {why}")

        else:
            # set sourec and project to their user input values
            project["enhanced_video"] = enhanced_video
            if raw_video is not None:
                project["raw_video"] = raw_video

        if notes is not None and not notes.isspace() and notes:
            notes_file_name = proj_name + "_notes.txt"
            notes_file = path.joinpath(notes_file_name)
            project["notes"] = notes

            try:
                with open(notes_file, 'w') as n_file:
                    n_file.write(notes)
            except IOError as error:
                message = f"Can't open file for notes {error}"
                qw.QMessageBox.critical(self, "Error making writing notes", message)

        project['enhanced_video_path'] = enhanced_video.parent
        project['enhanced_video_no_path'] = enhanced_video.name
        project['enhanced_video_no_extension'] = enhanced_video.stem

        if raw_video is not None:
            project['raw_video_path'] = raw_video.parent
            project['raw_video_no_path'] = raw_video.name
            project['raw_video_no_extension'] = raw_video.stem

        if stats_from_enhanced:
            project["stats_from_enhanced"] = True
        else:
            project["stats_from_enhanced"] = False

        project["results"] = VideoAnalysisResultsStore(self)
        project["results"].data_changed.connect(self.data_changed)

        self._project = project
        self.set_video_scale_parameters()
        self.save_project()
        self.project_created_or_loaded()

    @qc.pyqtSlot(int)
    def data_changed(self, value):
        """
        notify all widgets of a change in the data
            Args:
                value (int) code for type of data changed, 0: any 1: region
        """
        if value == 1:
            self._drawingWidget.update_data_display()

    @qc.pyqtSlot()
    def set_video_scale_parameters(self):
        """
        get the video scaling parameters from the user
            Returns:
                None
        """
        if self._project is None:
            return

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

        fps, res, units = VideoParametersDialog.get_values_from_user(self,
                                                                     fps,
                                                                     resolution,
                                                                     units)

        self._project['frame_rate'] = fps
        self._project['resolution'] = res
        self._project['resolution_units'] = units

        self.display_properties()

    def get_fps_and_resolution(self):
        """
        getter for the frames per second and the resolution of the video

            Returns:
                frames per second (int), resolution (float)
        """
        if self._project is not None:
            return int(self._project["frame_rate"]), float(self._project["resolution"])

        return None, None

    def get_results(self):
        """
        getter for the current results object

            Return:
                the current results object
        """
        if self._project:
            return self._project["results"]

        return None

    def get_project(self):
        """
        getter for the project
            Returns:
                (CGTProjcet) the current project
        """
        return self._project

    def append_region(self, region):
        """
        add a region to the results and notify the crystal drawing widget
            Args:
                region (QRect) the region
        """
        self._project["results"].add_region(region)

    def remove_region(self, region):
        """
        remove a region from the results and notify the crystal drawing widget
            Args:
                region (QRect) the region
        """
        index = self._project["results"].get_regions().index(region)
        self._project["results"].remove_region(index)

    def region_has_markers(self, region):
        """
        check if a region has markers
            Args:
                region (QGraphicsRectItem) the region
            Returns:
                True if has marker else false
        """
        index = self._project["results"].get_regions().index(region)
        markers = []
        markers.append(self._project["results"].get_lines_for_region(index))
        markers.append(self._project["results"].get_points_for_region(index))
        markers = [x for x in markers if x is not None]

        return len(markers)>0

    def append_lines(self, region_index, lines):
        """
        add a list of lines to a region
            Args:
                region_index (int) the array index of the region
                lines [Line] array of lines to be added
            Returns:
                None
        """
        for line in lines:
            self._project["results"].add_line(region_index, line)

        #self._drawingWidget.new_region()
        self._resultsWidget.display_data()

    def set_title(self):
        """
        sets window title

            Returns:
                None
        """
        name = self._translated_name

        if self._project is not None and self._project["proj_name"] is not None:
            proj_name = self._project["proj_name"]
            name += f": {proj_name}"

        self.setWindowTitle(name)

    @qc.pyqtSlot()
    def set_view_properties(self):
        """
        get display properties from the user
        """
        msg_box = qw.QMessageBox()
        msg_box.setText(self.tr("Select Property"))
        new_line = msg_box.addButton(self.tr("Drawing Line Colour"), qw.QMessageBox.NoRole)
        old_line = msg_box.addButton(self.tr("Display Line Colour"), qw.QMessageBox.NoRole)
        line_width = msg_box.addButton(self.tr("Line Width"), qw.QMessageBox.NoRole)
        msg_box.addButton(self.tr("Cancel"), qw.QMessageBox.NoRole)
        msg_box.exec()

        if msg_box.clickedButton() == new_line:
            drawing_colour = self.get_colour()
            if drawing_colour is not None:
                self._pens.set_drawing_colour(drawing_colour)
                self.redraw_markers()
        elif msg_box.clickedButton() == old_line:
            dispaly_colour = self.get_colour()
            if dispaly_colour is not None:
                self._pens.set_display_colour(dispaly_colour)
                self.redraw_markers()
        elif msg_box.clickedButton() == line_width:
            width = qw.QInputDialog.getInt(self,
                                           self.tr("Line Width"),
                                           self.tr("Line Width"),
                                           value = PenStore.DEFAULT_WIDTH,
                                           min = 1,
                                           max = 15,
                                           step = 1)
            if width[1]:
                self._pens.set_drawing_and_display_width(width[0])
                self.redraw_markers()

    def get_colour(self):
        """
        get a colour from the user
        """
        colour = qw.QColorDialog.getColor(qt.Qt.red, self)
        if colour.isValid():
            return colour

        return None

    @qc.pyqtSlot()
    def load_video(self):
        """
        read in a video and display
            Returns:
                True if successful, else False
        """
        error_title = self.tr("CGT Video File Error")
        if self._project is None:
            message = self.tr("You must load/create a project before loading video")
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return False

        if self._project["enhanced_video"] is None:
            message = self.tr("The current project contains no video file")
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return False

        video_file = pathlib.Path(self._project["enhanced_video"])
        if not video_file.exists():
            message = self.tr("Can't find file {}")
            message = message.format(self._project["enhanced_video"])
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return False

        self.setup_video_source(video_file)
        return True

    def setup_video_source(self, video_file):
        """
        make the video readers
            Args:
                video_file (palthlib.Path): the file holding the video
        """
        try:
            # make the objects
            self._enhanced_video_reader = VideoSource(str(video_file),
                                                      float(self._project["frame_rate"]))
            self._selectWidget.set_video_source(self._enhanced_video_reader)
            self._drawingWidget.set_video_source(self._enhanced_video_reader)
            self._resultsWidget.set_video_source(self._enhanced_video_reader)

            if self._project["raw_video"] is not None:
                if self._project["stats_from_enhanced"]:
                    self._videoStatsWidget.set_video_source(self._enhanced_video_reader)
                else:
                    self._raw_video_reader = VideoSource(self._project["raw_video"],
                                                         float(self._project["frame_rate"]))
                    self._videoStatsWidget.set_video_source(self._raw_video_reader)
            else:
                self._videoStatsWidget.set_video_source(self._enhanced_video_reader)

            stats = self.get_results().get_video_statistics()
            if stats is not None and len(stats.get_frames()) > 0:
                self._videoStatsWidget.display_stats()

        except ffmpeg.Error as error:
            self.display_error(f"File {video_file} cannot be probed: {error}")
            return False
        except StopIteration:
            self.display_error(f"File {video_file} does not appear to contain video information")
            return False
        except KeyError as exception:
            self.display_error(f"Probe video data error: unknown key {exception}")
            return False

        return True

    qc.pyqtSlot()
    def save_region_videos(self):
        """
        save videos of the regions
        """
        results = self._project["results"]
        if len(results.get_regions()) < 1:
            error_title = self.tr("CGT Error")
            message = self.tr("You must have at least one region.")
            qw.QMessageBox.warning(self,
                                   error_title,
                                   message)
            return

        dir_name = qw.QFileDialog.getExistingDirectory(
            self,
            self.tr("Select the directory for output. Existing files will be overwritten."),
            os.path.expanduser('~'))

        if not dir_name:
            return

        region_copy = RegionVideoCopy(self._project)
        region_copy.copy_region_videos(dir_name)

    def has_unsaved_data(self):
        """
        find if window is holding unsaved data

            Returns:
                True if unsaved data is held, False otherwise
        """
        return self._project is not None and self._project.has_been_changed()

    @qc.pyqtSlot()
    def edit_notes(self):
        """
        allow the user the edit the projects notes
        """
        if self._project is None:
            return

        ew = EditNotesDialog(self, self._project)
        ew.show()

    @qc.pyqtSlot()
    def make_video_statistics(self):
        """
        calculate the intensity statistics for the video
        """
        if self._project is None:
            return

        if self._tabWidget.currentWidget() != self._videoStatsTab:
            return

        if self._project["results"].get_video_statistics() is not None:
            message = self.tr("You already have statistics for this video. Replace?")
            mb_reply = qw.QMessageBox.question(self,
                                              'CrystalGrowthTracker',
                                              message,
                                              qw.QMessageBox.Yes | qw.QMessageBox.No,
                                              qw.QMessageBox.No)

            if mb_reply == qw.QMessageBox.No:
                return

        analyser = None
        if self._project["raw_video"] is not None:
            analyser = VideoAnalyser(str(self._project["raw_video"]), self)
        else:
            analyser = VideoAnalyser(str(self._project["enhanced_video"]), self)

        self._progressBar.setMaximum(analyser.get_number_frames())
        analyser.frames_analysed.connect(self._progressBar.setValue)
        self._progressBar.show()

        self._project["results"].set_video_statistics(analyser.stats_whole_film())
        self._progressBar.hide()

        self._videoStatsWidget.display_stats()
        self._videoStatsWidget.enable(True)

    def make_report(self):
        """
        make a html report
        """
        report_file = None

        self._progressBar.setMaximum(8)
        maker = ReportMaker(self)
        maker.stage_completed.connect(self._progressBar.setValue)
        self._progressBar.show()
        try:
            report_file = maker.save_html_report(self)
        except (IOError, OSError, EOFError) as exception:
            qw.QMessageBox.critical(self,
                                    self.tr("Auto Save Report"),
                                    str(exception))
            report_file = None
        finally:
            self._progressBar.hide()
        return report_file

    def get_video_stats(self):
        """
        getter for video stats
            Returns:
                video stats array
        """
        return self._project["results"].get_video_statistics()

    def redraw_markers(self):
        """
        redraw all the markers with new colour/width
        """
        self._project["results"].change_marker_props(self._pens)
        self._drawingWidget.change_entry_pens()

    @qc.pyqtSlot()
    def closeEvent(self, event):
        """
        Overrides QWidget.closeEvent
        This will be called whenever a MyApp object recieves a QCloseEvent.
        All actions required befor closing widget are here.
            Args:
                event (QEvent) the Qt event object
        """
        message = self.tr('Do you want to leave?')
        changed = self.tr('You have unsaved data.')

        if self.has_unsaved_data():
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

            # to get rid tell the event-loop to schedule for deleteion
            # do not destroy as a pointer may survive in event-loop
            # which will trigger errors if it recieves a queued signal
            self.deleteLater()

        else:
            # dispose of the event in the approved way
            event.ignore()

    @staticmethod
    def setup_tab(tab, widget):
        """
        connect widget to tab via layout (allows resizing)
            Args:
                tab (QWidget) the page widget from a tab
                widget (QWidget) the widget to be added
        """
        layout = qw.QVBoxLayout()
        layout.addWidget(widget)
        tab.setLayout(layout)

    def get_enhanced_reader(self):
        """
        getter for the enhanced video reader
        """
        return self._enhanced_video_reader
