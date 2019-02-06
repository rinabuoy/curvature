import numpy as np
import pandas as pd
import glob
import os
from curvature import Curvature
from plotting import PlottingCurvature, PlottingDistributions
import matplotlib.pyplot as plt
from itertools import combinations


class Ventricle:

    def __init__(self, case_name, view):
        self.case_name = case_name
        self.view = view
        self.id = None
        self.number_of_frames = 0
        self.number_of_points = 0
        self.es_frame = 0
        self.ed_frame = 0
        self.apex = 0
        self.ventricle_curvature = []
        self.vc_normalized = []  # ventricle_curvature normalized
        self.apices = []
        self.data = self._read_echopac_output()
        self.biomarkers = pd.DataFrame(index=[self.id])
        self.get_curvature_per_frame()
        self.get_normalized_curvature()
        self.find_apices()
        self.find_ed_and_es_frame()

    def _read_echopac_output(self):
        with open(self.case_name) as f:
            for line in f:
                if 'ID=' in line:
                    self.id = line.split('=')[1].strip('\n')
                    f.close()
                    break

        data = pd.read_csv(filepath_or_buffer=self.case_name, sep=',', skiprows=10, header=None, delim_whitespace=False)
        data.dropna(axis=1, inplace=True)
        data = data.values
        self.number_of_frames, self.number_of_points = data.shape[0], int(data.shape[1]/2)
        return data

    @staticmethod
    def _plane_area(x, y):
        return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    def find_ed_and_es_frame(self):
        areas = np.zeros(self.number_of_frames)
        for frame in range(self.number_of_frames):
            x, y = self.data[frame, ::2], self.data[frame, 1::2]
            areas[frame] = self._plane_area(x, y)
        self.es_frame, self.ed_frame = np.argmin(areas), np.argmax(areas)

    def get_curvature_per_frame(self):
        for frame in range(self.number_of_frames):
            xy = [[x, y] for x, y in zip(self.data[frame][::2], self.data[frame][1::2])]
            curva = Curvature(line=xy)
            self.ventricle_curvature.append(curva.calculate_curvature(gap=0))
        self.ventricle_curvature = np.array(self.ventricle_curvature)

    def find_apices(self):
        for frame in range(self.number_of_frames):
            # self.apices.append(np.argmax(self.ventricle_curvature[frame]))  # Maximum curvature in given frame
            self.apices.append(np.argmin(self.data[frame, 1::2]))  # Lowest point in given frame
        values, counts = np.unique(self.apices, return_counts=True)
        self.apex = values[np.argmax(counts)]  # Lowest point in all frames
        # self.apex = self.apices[self.ed_frame]  # Lowest point at end diastole

    def get_normalized_curvature(self):
        # Empirically established values. Useful for coloring, where values cannot be negative.
        self.vc_normalized = [(single_curvature+0.125)*4 for single_curvature in self.ventricle_curvature]

    def get_biomarkers(self):

        curv = pd.DataFrame(data=self.ventricle_curvature)

        curv_max_col = curv.max(axis=0).idxmax()

        if self.view == '2C':
            curv_min_col = curv.min(axis=0).idxmin()
            curv_min_row = curv.min(axis=1).idxmin()
        else:
            _t = int(self.view == '4C')
            lower_bound = int(np.round((_t * 0.04 + (1 - _t) * 0.6) * len(curv.columns)))
            upper_bound = int(np.round((_t * 0.4 + (1 - _t) * 0.96) * len(curv.columns)))

            # id of the column (point number) with minimum value
            curv_min_col = curv.loc[:, lower_bound:upper_bound].min(axis=0).idxmin()

            # id of the row (frame) with minimum value
            curv_min_row = curv.loc[:, lower_bound:upper_bound].min(axis=1).idxmin()

        self.biomarkers['min'] = curv.min().min()
        self.biomarkers['max'] = curv.max().max()
        self.biomarkers['min_delta'] = np.abs(curv[curv_min_col].max() - self.biomarkers['min'])
        self.biomarkers['max_delta'] = np.abs(curv[curv_max_col].min() - self.biomarkers['max'])
        self.biomarkers['amplitude_at_t'] = np.abs(curv.loc[curv_min_row].max() - self.biomarkers['min'])

        return self.biomarkers


class Cohort:

    def __init__(self, source_path='data', view='4C', output_path='data', output='_all_cases.csv'):

        self.view = view
        self.source_path = source_path
        self.output_path = self._check_directory(output_path)
        self.output = output
        self.files = glob.glob(os.path.join(self.source_path, self.view, '*.CSV'))
        self.files.sort()
        self.df_all_cases = None
        self.df_master = None
        self.curv = None
        self.biomarkers = None

    def _set_paths_and_files(self, view='4C', output_path=''):
        self.view = view
        self.files = glob.glob(os.path.join(self.source_path, self.view, '*.CSV'))
        self.files.sort()
        self.output_path = self._check_directory(output_path)

    @staticmethod
    def _check_directory(directory):
        if not os.path.isdir(directory):
            os.mkdir(directory)
        return directory

    def _try_get_data(self, data=False, master_table=False):

        if data:
            _data_file = os.path.join(self.output_path, self.view, 'output_EDA', self.output)

            if os.path.isfile(_data_file):
                self.df_all_cases = pd.read_csv(_data_file, header=0, index_col=0)


            if not os.path.exists(_data_file):
                self._build_data_set(to_file=True)
            self.biomarkers = self.df_all_cases.columns

            # if self.df_all_cases is None:
            #     self.df_all_cases = pd.read_csv(_data_file, header=0, index_col=0)

        if master_table:
            _master_table_file = os.path.join(self.output_path, 'master_table.csv')

            if os.path.isfile(_master_table_file):
                self.df_master = pd.read_csv(_master_table_file, header=0, index_col=0)

            if not os.path.exists(_master_table_file):
                self._build_master_table(to_file=True)

            # if self.df_master is None:
            #     self.df_master = pd.read_csv(_master_table_file, header=0, index_col=0)

        if not (data or master_table):
            exit('No data has been created, set the data or master_table parameter to True')

    def _build_data_set(self, to_file=False):

        list_of_dfs = []
        for curv_file in self.files:
            print('case: {}'.format(curv_file))
            ven = Ventricle(curv_file, view=self.view)
            list_of_dfs.append(ven.get_biomarkers())

        self.df_all_cases = pd.concat(list_of_dfs)
        self.df_all_cases['min_index2'] = np.abs(self.df_all_cases['min_delta'] / self.df_all_cases['min'])
        self.df_all_cases['min_index'] = np.abs(self.df_all_cases['min_delta'] * self.df_all_cases['min']) * 1000
        self.df_all_cases['log_min_index'] = np.log(self.df_all_cases['min_index'])
        self.df_all_cases['min_v_amp_index'] = self.df_all_cases['min_delta'] * self.df_all_cases['amplitude_at_t']*1000
        self.df_all_cases['log_min_v_amp_index'] = np.log(self.df_all_cases['min_v_amp_index'])
        self.df_all_cases['delta_ratio'] = self.df_all_cases['min_delta'] / self.df_all_cases['max_delta']

        if to_file:
            self.df_all_cases.to_csv(os.path.join(self.output_path, self.view, 'output_EDA', self.output))

    def _build_master_table(self, to_file=False, views=('4C', '3C', '2C')):

        list_of_dfs = []

        for view in views:
            self._set_paths_and_files(view=view, output_path=self.output_path)
            self._try_get_data(data=True)
            self.df_all_cases.columns = [self.view + '_' + col for col in self.df_all_cases.columns]
            list_of_dfs.append(self.df_all_cases)

        self.df_master = list_of_dfs[0]
        for df_i in range(1, len(list_of_dfs)):
            self.df_master = self.df_master.merge(list_of_dfs[df_i], right_index=True, left_index=True, sort=True)
        if to_file:
            self.df_master.to_csv(os.path.join(self.output_path, 'master_table.csv'))

    def plot_curvatures(self, coloring_scheme='curvature'):

        _source_path = os.path.join(self.source_path, self.view)
        _output_path = self._check_directory(os.path.join(self.output_path, self.view, 'output_curvature'))

        for case in self.files:
            ven = Ventricle(case_name=case, view=self.view)
            print(ven.id)
            print('Points: {}'.format(ven.number_of_points))
            plot_tool = PlottingCurvature(source=_source_path,
                                          output_path=_output_path,
                                          ventricle=ven)
            plot_tool.plot_all_frames(coloring_scheme=coloring_scheme)

    def plot_distributions(self, plot_data=False, plot_master=False):

        if plot_data:
            if self.df_all_cases is None:
                self._try_get_data(data=True)

            _view_output_path = self._check_directory(os.path.join(self.output_path, self.view, 'output_EDA'))

            plot_tool = PlottingDistributions(self.df_all_cases, '', _view_output_path)
            for col in self.biomarkers:
                plot_tool.set_series(col)
                plot_tool.plot_distribution()

            col_combs = combinations(self.biomarkers, 2)
            for comb in col_combs:
                plot_tool.plot_2_distributions(comb[0], comb[1], kind='kde')

        if plot_master:
            if self.df_master is None:
                self._try_get_data(master_table=True)

            _master_output_path = self._check_directory(os.path.join(self.output_path, 'output_master'))
            master_plot_tool = PlottingDistributions(self.df_master, '', _master_output_path)

            for col in self.biomarkers:
                master_plot_tool.plot_2_distributions('4C_'+col, '3C_'+col, kind='kde')

    def get_extemes(self, n=30):

        self._try_get_data(data=True)

        list_of_extremes = []
        for col in self.df_all_cases.columns:
            list_of_extremes.append(self.df_all_cases[col].sort_values(ascending=False).index.values[:n])
            list_of_extremes.append(self.df_all_cases[col].sort_values(ascending=False).values[:n])

        index_lists = [2 * [i] for i in self.df_all_cases.columns]
        index = [item for sublist in index_lists for item in sublist]

        df_extremes = pd.DataFrame(list_of_extremes, index=index)
        _output_path = self._check_directory(os.path.join(self.output_path, self.view, 'output_EDA'))
        df_extremes.to_csv(os.path.join(_output_path, 'extremes.csv'))


if __name__ == '__main__':

    for _view in ['2C']:

        source = os.path.join('/home/mat/Python/data/curvature')
        target_path = os.path.join('/home/mat/Python/data/curvature/')

        cohort = Cohort(source_path=source, view=_view, output_path=target_path)

        # cohort.get_extemes(32)
        # cohort.plot_curvatures('asf')
        # cohort.plot_curvatures()
        cohort.plot_distributions(plot_master=True)
