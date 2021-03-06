import numpy as np
import pandas as pd
from pandas.plotting import parallel_coordinates
from scipy.stats import kruskal, levene, ttest_ind, normaltest, spearmanr, pearsonr
import os
import matplotlib.pyplot as plt
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
import seaborn as sns
from plotting import PlottingDistributions
from LV_edgedetection import check_directory
import statsmodels.api as sm


class StatAnalysis:

    COLUMNS = ['min', 'max', 'avg_min_basal_curv', 'avg_avg_basal_curv', 'min_delta', 'max_delta',
               'amplitude_at_t', 'Series_SOP', 'Patient_ID']

    def __init__(self, input_path, output_path, data_filename):
        self.input_path = input_path
        self.output_path = output_path
        self.data_filename = data_filename
        self.df = self.read_dataframe(index_col='patient_ID')

    def read_dataframe(self, index_col='patient_ID'):
        return pd.read_csv(os.path.join(self.input_path, self.data_filename), index_col=index_col, header=0)

    @staticmethod
    def pop_std(x):
        return x.std(ddof=0)

    def variance_test(self, group_a, group_b):
        print('-----Variance test--------------------------------------------------')
        df_a = self.df[group_a]
        df_b = self.df[group_b]
        t_l, p_l = levene(df_a, df_b)
        print('Statistic: {} and p-value: {} of variance comparison'.format(t_l, p_l))
        print('-----END Variance test----------------------------------------------\n')
        # https://docs.scipy.org/doc/scipy - 0.14.0/reference/generated/scipy.stats.levene.html

    def _check_normality_assumptions(self, feature):

        print('-----Normality test-------------------------------------------------')
        print('This function tests the null hypothesis that a sample comes from a normal distribution. ')
        print('It is based on D’Agostino and Pearson’s [1], [2] test that combines skew and kurtosis '
              'to produce an omnibus test of normality.')
        # https://docs.scipy.org/doc/scipy - 0.14.0/reference/generated/scipy.stats.normaltest.html
        t_nt_control, p_nt_control = normaltest(self.df[feature])
        print('Statistic: {} and p-value: {} of controls normality test'.format(t_nt_control, p_nt_control))
        print('-----END Normality test--------------------------------------------\n')
        return t_nt_control, p_nt_control

    def _correlation(self, feature1, feature2):
        print('-----Spearman correlation-------------------------------------------------')
        print('The Spearman correlation is a nonparametric measure of the monotonicity of the relationship between ')
        print('two datasets. Unlike the Pearson correlation, ')
        print('the Spearman correlation does not assume that both datasets are normally distributed. ')
        print('P-value smaller than 0.05 means that the null hypothesis that the two features are not correlated')
        print('can be rejected.')
        sp_rho, sp_pv = spearmanr(self.df[feature1], self.df[feature2])
        print('Correlation between {} and {}'.format(feature1, feature2))
        print('Statistic: {} and p-value: {} of the spearman correlation test'.format(sp_rho, sp_pv))
        print('-----END Spearman correlation--------------------------------------------\n')

        return sp_rho, sp_pv

    def _multiple_non_parametric_test(self):
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.kruskal.html

        t_k, p_k = kruskal(self.controls, self.htn, self.bsh)
        print('-----Kruskal-Willis--------------------------------------------------')
        print('Comparison across all groups')
        print('Shows that there is a significance in differences among the distribution.')
        print('Null hypothesis: distribution(controls) == distribution(htn) == distribution(bsh)')
        print('Statistic: {} and p-value: {} of kruskal analysis'.format(t_k, p_k))
        print('-----END Kruskal-Willis----------------------------------------------\n')
        return p_k

    def _welchs_t_test(self, covariate, group_a, group_b):

        df_a = self.df[group_a]
        df_b = self.df[group_b]

        print('-----Pairwise t-test--------------------------------------------')
        print('Show that there is a diffence in medians between the groups. Use equal_var = False to perform'
              'the Welch\'s test')
        print('T_test, returning one-sided p-value:')
        t_t, p_val = ttest_ind(df_a, df_b, equal_var=False)
        print('Statistic: {} and p-value: {} of t-test analysis '
              'on control vs htn groups'.format(t_t, p_val))
        print('-----END Pairwise t-test-------------------------------------------\n')

    def perform_analysis(self, covariates=('avg_basal_ED',)):
        if self.df is None:
            self.read_dataframe()

        df_description = pd.DataFrame(columns=covariates)

        for cov in covariates:
            # Check the basic descriptors
            df_cov = self.df[cov]

            print('----------------------------------------------')
            print('----------------------------------------------')
            print('Univariate tests on covariate {}'.format(cov))
            print('----------------------------------------------')
            # print(self.controls)
            print('Control mean: {} and std: {} of {}'.format(df_cov.mean(),
                                                              df_cov.std(),
                                                              df_cov.describe(),
                                                              cov))
            n_stat, n_p = self._check_normality_assumptions(cov)
            df_description[cov] = df_cov.describe(percentiles=[.15, .25, .5, .75, .85])
            df_description.loc['normality_stat', cov] = n_stat
            df_description.loc['normality_p', cov] = n_p
        df_description.to_csv(os.path.join(self.input_path, 'Statistical values.csv'))

        correlations = []
        for i in range(3):
            sp_rho, sp_pv = self._correlation(covariates[0], covariates[1])
            correlations.append(dict(f1=covariates[0], f2=covariates[1], sp_rho=sp_rho, sp_pv=sp_pv))
            covariates = np.roll(np.array(covariates), 1)

        df_combinations = pd.DataFrame(correlations)
        df_combinations.assign(strength=['weak' if np.abs(x) <= 0.3 else 'moderate' if np.abs(x) <= 0.7 else 'strong'
                                         for x in df_combinations.sp_rho])
        df_combinations.to_csv(os.path.join(self.input_path, 'Correlations.csv'))

        # self._multiple_non_parametric_test()
        # self._welchs_t_test(cov,)

    def plot_boxplots(self, covariates=('Average septal curvature $[cm^{-1}]$',), hue='SB'):
        plot_tool = PlottingDistributions(self.df[self.df[hue] <3], covariates[0], output_path=self.output_path)
        # self.df = self.df[self.df.SB>0]
        for cov in covariates:
            plot_tool.series = cov
            plot_tool.plot_multiple_boxplots(group_by=hue)

    def plot_histograms(self, covariates=('avg_min_basal_curv',)):
        for cov in covariates:
            sns.distplot(self.df.loc[self.df[r'85 percentile curv'] < 3][cov], kde=False, rug=True, color='r', bins=12)
            sns.distplot(self.df.loc[self.df[r'85 percentile curv'] == 3][cov], kde=False, rug=True, color='g', bins=6)
            # plt.legend()

            if 'Average septal curvature' in cov:
                plt.xlabel(r'Average septal curvature $[dm^{-1}]$', fontsize=23)
                plt.ylabel('Frequency', fontsize=30)
            else:
                plt.ylabel('')
                plt.xlabel(cov, fontsize=23)
            plt.xticks(fontsize=16)
            plt.yticks(fontsize=16)

            plt.tight_layout()
            plt.savefig(os.path.join(self.output_path, '{} histogram.svg'.format(cov)))
            plt.clf()
            plt.close()

        # plt.figure()
        # parallel_coordinates(self.df[['SB', r'Average septal curvature [cm-1]',
        #                               r'Wall thickness ratio in PLAX view measurements',
        #                               r'Wall thickness ratio in 4CH view measurements']], 'SB')
        # plt.savefig(os.path.join(self.output_path, 'covariate_distributions.png'))

    def plot_relations(self, pairs=('min', 'max')):
        plot_tool = PlottingDistributions(self.df, pairs[0][0], output_path=self.output_path)
        for pair in pairs:
            plot_tool.plot_with_labels(pair[0], pair[1])


class StrainAnalysis:

    FACTORS_BASIC = [r'strain_avc_Basal Septal']
    FACTORS_WITH_MW = ['GWI', 'MW_Basal Septal', 'MW_Mid Septal', 'MW_Apical Septal', 'PSS_Basal Septal',
                       'PSS_Mid Septal', 'PSS_Apical Septal', 'strain_avc_Basal Septal', 'strain_avc_Mid Septal',
                       'strain_avc_Apical Septal', 'max_gls_before_avc', 'max_gls']

    def __init__(self, patient_data_path, curvature_results_path, output_path, merged_data_filename,
                 measurements_filename=None, twodstrain_filename=None, patient_data_filename=None, curvature_filename=None):

        self.patient_data_path = patient_data_path
        self.curvature_results_path = curvature_results_path
        self.output_path = output_path

        self.measurements_filename = measurements_filename
        self.twodstrain_filename = twodstrain_filename
        self.patient_data_filename = patient_data_filename
        self.curvature_filename = curvature_filename

        # self.df_meas = pd.read_excel(os.path.join(self.patient_data_path, self.measurements_filename),
        #                              index_col='ID', header=0)
        # self.df_2ds = pd.read_excel(os.path.join(self.patient_data_path, self.twodstrain_filename),
        #                             index_col='ID', header=0)
        # if not(os.path.isfile(os.path.join(self.curvature_results_path, merged_data_filename))):
        #     self.get_min_ed_rows(True)
        #     self.combine_measurements_2ds(True)

        self.df_comparison = pd.read_csv(os.path.join(self.patient_data_path, merged_data_filename),
                                         index_col='patient_ID', header=0)
        self.df_comparison['curv_threshold'] = (self.df_comparison['Average septal curvature [cm-1]']
                                                < -0.9).astype(int) #+ 1 # CHANGE SIGN!!!!!!

        self.models = {}

    # ---Processing and combining dataframes----------------------------------------------------------------------------

    def get_min_ed_rows(self, to_file=False):
        """
        Find cases (index level = 0) where the end diastolic trace's curvature is the lowest. Used in case a single
        case has a few views/strain measurements done.
        :param to_file: Whether to save the result to a file.
        """
        df_curv_full = pd.read_csv(os.path.join(self.curvature_results_path, self.curvature_filename),
                                   index_col=['patient_ID', 'patient_ID_detail'], header=0)
        df_curv_full.dropna(inplace=True)

        df_curv = df_curv_full.loc[df_curv_full.groupby(level=0).min_ED.idxmin().values]
        df_curv.reset_index(level=1, inplace=True)

        if to_file:
            df_curv.to_csv(os.path.join(self.output_path, 'curv_min_ED.csv'))

    def combine_measurements_2ds(self, to_file=False):
        """
        Combine information from 3 different sources: 2DStrain (parsed xml export), measurements of WT and curvature
        indices.
        :param to_file: Whether to save the result to a file.
        """

        exit('Run only if really necessary! If so, update RGM and RFNA (files in export, 1.11.2019)')

        relevant_columns = ['patient_ID_detail', 'min', 'min_delta', 'avg_min_basal_curv', 'avg_avg_basal_curv',
                            'min_ED', 'min_delta_ED', 'avg_basal_ED', 'SB', 'min_index', 'min_index_ED',
                            'strain_avc_Apical Lateral', 'strain_avc_Apical Septal', 'strain_avc_Basal Lateral',
                            'strain_avc_Basal Septal', 'strain_avc_Mid Lateral', 'strain_avc_Mid Septal',
                            'strain_min_Apical Lateral', 'strain_min_Apical Septal', 'strain_min_Basal Lateral',
                            'strain_min_Basal Septal', 'strain_min_Mid Lateral', 'strain_min_Mid Septal',
                            'max_gls_before_avc', 'max_gls', 'max_gls_time', r'IVSd (basal) PLAX', r'IVSd (mid) PLAX',
                            r'PLAX basal/mid', r'IVSd (basal) 4C', r'IVSd (mid) 4C', r'4C basal/mid', 'SB_meas']

        self.df_curv = pd.read_csv(os.path.join(self.output_path, 'curv_min_ED.csv'), header=0, index_col='patient_ID')

        df_meas_2ds = self.df_curv.join(self.df_2ds, how='outer')  # no on= because it's joined on indexes
        df_meas_2ds = df_meas_2ds.join(self.df_meas, how='outer', rsuffix='_meas')
        df_meas_2ds = df_meas_2ds[relevant_columns]

        if to_file:
            df_meas_2ds.index.name = 'patient_ID'
            df_meas_2ds.to_csv(os.path.join(self.output_path, 'Measurements_and_2Dstrain.csv'))

    def plots_wt_and_curvature_vs_markers(self, save_figures=False):

        plot_dir = check_directory(os.path.join(self.output_path, 'plots'))

        x_labels = ['min_ED', 'avg_min_basal_curv', r'PLAX basal/mid', r'4C basal/mid', 'avg_basal_ED']

        for x_label in x_labels:
            for y_label in self.FACTORS_BASIC:

                if x_label in ['PLAX basal_mid', '4C basal_mid']:
                    plt.axvline(1.4, linestyle='--', c='k')
                    self.df_comparison.plot(x=x_label, y=y_label, c='SB', kind='scatter', legend=True, colorbar=True,
                                            cmap='winter', title='Relation of {} to {}'.format(y_label, x_label))
                else:
                    self.df_comparison.plot(x=x_label, y=y_label, c=x_label, kind='scatter', legend=True, colorbar=True,
                                            cmap='autumn', title='Relation of {} to {}'.format(y_label, x_label))
                if save_figures:
                    plt.savefig(os.path.join(plot_dir, r'{} vs {} HTNs.png'.format(y_label, x_label.replace('/', '_'))))
                else:
                    plt.show()
                plt.close()

    def plot_curv_vs_wt(self, save_figures=False, w_reg=False):

        plot_dir = check_directory(os.path.join(self.output_path, 'plots'))
        x_labels = [r'PLAX basal/mid', r'4C basal/mid', 'IVSd (basal) PLAX', 'IVSd (mid) PLAX', 'IVSd (basal) 4C',
                    'IVSd (mid) 4C']
        y_labels = ['min_ED', 'avg_basal_ED', 'avg_min_basal_curv']

        # for x_label in x_labels:
        #     for y_label in y_labels:
        #         self.df_comparison.plot(x=x_label, y=y_label, c='SB', kind='scatter', legend=True, colorbar=True,
        #                                 cmap='winter', title='Relation of {} to {}'.format(y_label, x_label))
        #         means_x = self.df_comparison.groupby('SB')[x_label].mean()
        #         means_y = self.df_comparison.groupby('SB')[y_label].mean()
        #         plt.plot(means_x, means_y, 'kd')
        #
        #         if x_label in [r'PLAX basal/mid', r'4C basal/mid']:
        #             plt.axvline(1.4, linestyle='--', c='k')
        #         if save_figures:
        #             plt.savefig(os.path.join(plot_dir, r'Meas {} vs {} HTNs.png'.format(y_label,
        #                                                                                 x_label.replace('/', '_'))))
        #         else:
        #             plt.show()
        #         plt.close()

        # print('Curvature below -1: {}'.format(self.df_comparison.curv_threshold.sum()))
        # print('4C above 1.4: {}'.format((self.df_comparison['4C basal/mid'] > 1.4).sum()))
        # print('PLAX above 1.4: {}'.format((self.df_comparison['PLAX basal/mid'] > 1.4).sum()))
        # print('SB cases: {}'.format((self.df_comparison.SB > 1).sum()))
        # 'Average septal curvature [cm-1]',
        # #                                  r'Wall thickness ratio in 4CH view',
        # #                                  r'Wall thickness ratio in PLAX view'
        from matplotlib import cm
        from matplotlib.colors import ListedColormap

        top = cm.get_cmap('Oranges_r', 128)
        bottom = cm.get_cmap('Blues', 128)
        newcolors = np.vstack((top(np.linspace(0, 1, 512)),
                               bottom(np.linspace(0, 1, 512))))
        newcmp = ListedColormap(newcolors, name='OrangeBlue')

        self.df_comparison.plot(x=r'Wall thickness ratio in PLAX view', y=r'Wall thickness ratio in 4CH view',
                                c='Average septal curvature [cm-1]', kind='scatter', legend=False, s=200,
                                colorbar=True, cmap=newcmp, title='',
                                figsize=(9, 7.2))
        # plt.title('Curvature values w.r.t. both WTR metrics', fontsize=26)
        plt.xlabel(r'Wall thickness ratio in PLAX view', fontsize=23)
        plt.ylabel(r'Wall thickness ratio in 4CH view', fontsize=23)

        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)
        plt.axvline(1.4, ymax=0.47, linestyle='--', c='k')
        plt.axhline(1.4, xmax=0.462, linestyle='--', c='k')
        plt.xlim((0.7, 2.2))
        plt.ylim((0.7, 2.2))
        plt.tight_layout()
        f = plt.gcf()
        f.get_axes()[1].set_ylabel('Average septal curvature $[dm^{-1}]$', fontsize=23)
        f.get_axes()[1].tick_params(labelsize=16)
        if save_figures:
            plt.savefig(os.path.join(plot_dir, r'Ratios_curvature.svg'))
        else:
            plt.show()

    def get_statistics(self, indices=()):

        df_stats = pd.DataFrame()

        for marker in self.FACTORS_BASIC:
            df_stats['sb_mean_'+marker] = self.df_comparison.groupby('SB')[marker].mean()
            df_stats['sb_sd_'+marker] = self.df_comparison.groupby('SB')[marker].std()
            df_stats['curv_mean_'+marker] = self.df_comparison.groupby('curv_threshold')[marker].mean()
            df_stats['curv_sd_' + marker] = self.df_comparison.groupby('curv_threshold')[marker].std()
        df_stats.to_csv(os.path.join(self.output_path, 'Simple_statistics.csv'))

    def linear_regression_basic_factors(self, to_file=False, show_plots=False):
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error, r2_score

        markers = ['Average septal curvature [cm-1]',
                   r'Wall thickness ratio in 4CH view',
                   r'Wall thickness ratio in PLAX view']

        list_results = []

        for marker in markers:
            for factor in self.FACTORS_BASIC:

                x = self.df_comparison[marker].values.reshape(-1, 1)
                y = self.df_comparison[factor].values.reshape(-1, 1)

                lr = LinearRegression()
                lr.fit(x, y)
                y_pred = lr.predict(x)
                rho_sp, p_sp = spearmanr(x, y)
                r_pe = pearsonr(x, y)

                dict_results = {'marker': marker, 'factor': factor, 'coefficients': lr.coef_, 'R2': r2_score(y, y_pred),
                                'mse': mean_squared_error(y, y_pred), 'spearmanr': rho_sp, 'spearmanp': p_sp,
                                'pearsonr': r_pe}

                list_results.append(dict_results)

                if show_plots:
                    plots = PlottingDistributions(self.df_comparison, 'min',
                                                  check_directory(os.path.join(self.output_path, 'plots')))
                    plots.plot_with_labels(series1=marker, series2=factor, w_labels=False)

        df_results = pd.DataFrame(list_results)

        if to_file:
            df_results.to_csv(os.path.join(self.output_path, 'Linear_regression_results.csv'))


class VariabilityAnalysis:
    OBSERVERS = ['F1', 'F2', 'M', 'J']
    MEASUREMENTS = ['PLAX basal', 'PLAX mid', '4C basal', '4C mid']

    def __init__(self, measurements_path, output_path, measurements_filename):
        self.measurements_path = measurements_path
        self.output_path = output_path
        self.measurements_filename = measurements_filename

        self.n_samples = 20
        self.df_wt = None
        self.df_curv = None
        self._read_data()

    def _read_data(self):

        df_file = os.path.join(self.measurements_path, self.measurements_filename)
        self.df_wt = pd.read_excel(df_file, sheet_name='WT_measurements', header=[0, 1], index_col=0)
        self.df_curv = pd.read_excel(df_file, sheet_name='Curvature', header=0, index_col='Study_id')
        self.df_test = pd.read_excel(df_file, sheet_name='Sheet2', header=[0, 1])
        self.df_test.columns = pd.MultiIndex.from_tuples(self.df_test.columns)  # Multi header: abs-rel/diff
        self.df_wt.columns = pd.MultiIndex.from_tuples(self.df_wt.columns)  # Multi index header: observer/measurements

    def calculate_sem_multi_index(self, view='PLAX', segment='basal', o1='F1', o2='F2', extended=False):

        assert view in ('PLAX', '4C'), 'Use only PLAX or 4C view'
        assert segment in ('basal', 'mid', 'ratio'), 'Use only basal or mid segment or ratio label'

        colname = ' '.join([view, segment])

        self.df_wt['SEM', 'Mean_measurement'] = (self.df_wt[o1, colname] + self.df_wt[o2, colname]) / 2
        self.df_wt['SEM', 'Difference'] = self.df_wt[o1, colname] - self.df_wt[o2, colname]
        self.df_wt['SEM', 'Difference_round'] = np.round(self.df_wt.SEM.Difference, decimals=2)
        self.df_wt['SEM', 'Difference_abs'] = np.abs(self.df_wt.SEM.Difference)
        self.df_wt['SEM', 'Difference_abs_round'] = np.round(self.df_wt.SEM.Difference_abs, decimals=2)

        if segment == 'ratio':
            df_range = pd.DataFrame(index=['_'.join([view, segment, o1, o2])])

            df_range['Min_measurement'] = self.df_wt.SEM.Mean_measurement.min()
            df_range['Max_measurement'] = self.df_wt.SEM.Mean_measurement.max()
            df_range['Range'] = df_range.Max_measurement - df_range.Min_measurement

            df_range['Min_error'] = self.df_wt.SEM.Difference_abs.min()
            df_range['Max_error'] = self.df_wt.SEM.Difference_abs.max()
            df_range['Range_error'] = df_range.Max_error - df_range.Min_error

            df_range['Mean_abs_error'] = np.mean(self.df_wt.SEM.Difference_abs)
            df_range['Sd_abs_error'] = np.std(self.df_wt.SEM.Difference_abs)

            df_range['Error_range_ratio'] = df_range.Range_error / df_range.Range
            df_range['Mean_abs_error_ratio'] = df_range.Mean_abs_error / df_range.Range
            df_range['Sd_abs_error_ratio'] = df_range.Sd_abs_error / df_range.Range
            return df_range

        return self.df_wt

    def calculate_sem_single_index(self, o1='F1', o2='F2', extended=False):

        self.df_curv['Mean_measurement'] = (self.df_curv[o1] + self.df_curv[o2]) / 2
        self.df_curv['Difference'] = self.df_curv[o1] - self.df_curv[o2]
        self.df_curv['Difference_round'] = np.round(self.df_curv.Difference, decimals=2)
        self.df_curv['Difference_abs'] = np.abs(self.df_curv.Difference)
        self.df_curv['Difference_abs_round'] = np.round(self.df_curv.Difference_abs, decimals=2)

        df_range = pd.DataFrame(index=['_'.join([o1, o2])])

        df_range['Min_measurement'] = self.df_curv.Mean_measurement.min()
        df_range['Max_measurement'] = self.df_curv.Mean_measurement.max()
        df_range['Range'] = df_range.Max_measurement - df_range.Min_measurement

        df_range['Min_error'] = self.df_curv.Difference_abs.min()
        df_range['Max_error'] = self.df_curv.Difference_abs.max()
        df_range['Range_error'] = df_range.Max_error - df_range.Min_error

        df_range['Mean_abs_error'] = np.mean(self.df_curv.Difference_abs)
        df_range['Sd_abs_error'] = np.std(self.df_curv.Difference_abs)

        df_range['Error_range_ratio'] = df_range.Range_error / df_range.Range
        df_range['Mean_abs_error_ratio'] = df_range.Mean_abs_error / df_range.Range
        df_range['Sd_abs_error_ratio'] = df_range.Sd_abs_error / df_range.Range

        # self.df_curv.to_csv(os.path.join(self.output_path, 'curv_{}_{}.csv'.format(o1, o2)))

        return df_range

    def _test_sem_calculations(self):  # function to ensure compliance with the theoretical values from the paper

        self.df_test['SEM', 'Absolute difference'] = sem((self.df_test.Measurement1.m, self.df_test.Measurement2.m),
                                                         ddof=1) * 2
        self.df_test['SEM', 'Individual SD'] = sem((self.df_test.Measurement1.m, self.df_test.Measurement2.m),
                                                   ddof=0) * 2
        self.df_test['SEM', 'Difference'] = self.df_test.Measurement1.m - self.df_test.Measurement2.m
        self.df_test['SEM', 'Mean measurement'] = (self.df_test.Measurement1.m + self.df_test.Measurement2.m) / 2
        self.df_test['SEM', 'Difference_round'] = np.round(self.df_test.SEM.Difference, decimals=2)
        print(self.df_test['SEM', 'Difference'])
        print(self.df_test['SEM', 'Mean measurement'])
        self.df_test['SEM', 'Difference_prcnt'] = self.df_test['SEM', 'Difference'] / self.df_test[
            'SEM', 'Mean measurement'] * 100
        self.df_test['SEM', 'Difference_prcnt_round'] = np.round(self.df_test['SEM', 'Difference_prcnt'])
        print(self.df_test[['Absolute intraobserver variability', 'SEM']])
        mean_sem = np.mean(self.df_test.SEM).round(decimals=2)
        sd_sem = np.std(self.df_test.SEM).round(decimals=3)
        print(mean_sem, sd_sem)

    def calculate_standard_error(self, sem_):

        factor = np.sqrt(2 * self.n_samples)  # np.sqrt(2 * n * (m - 1)), m === 2
        se_plus = sem_ * (1 + 1 / factor)
        se_minus = sem_ * (1 - 1 / factor)
        return se_plus, se_minus, sem_ / factor, 1 / factor

    def bland_altman_plot_multi_index(self, o1='F1', o2='F2', view='PLAX', segment='basal'):

        assert view in ('PLAX', '4C'), 'Use only PLAX or 4C view'
        assert segment in ('basal', 'mid', 'ratio'), 'Use only basal or mid segment or ratio label'

        cohort1 = self.df_wt[o1, ' '.join([view, segment])]
        cohort2 = self.df_wt[o2, ' '.join([view, segment])]

        _title = 'Observers O1 & {}'.format('O1*' if o2 == 'F2' else 'O2' if o2 == 'J' else 'O3')

        if segment == 'ratio':
            self.bland_altman_plot(cohort1, cohort2, title=_title,
                                   measurement='Wall thickness ratio', units='', xlimits=(0.7, 1.9),
                                   ylimits=(-0.7, 1.0))
        else:
            self.bland_altman_plot(cohort1, cohort2, title=_title,
                                   measurement='Wall thickness', units='[cm]', xlimits=(0.5, 1.6), ylimits=(-0.6, 1.0))
        # self.bland_altman_percentage_plot(cohort1, cohort2,
        # title=' '.join(['Wall thickness percent difference: F1 vs', o2, view, segment]))

    def bland_altman_plot_single_index(self, o1='F1', o2='F2'):

        cohort1 = self.df_curv[o1]
        cohort2 = self.df_curv[o2]

        _title = 'Observers O1 & {}'.format('O1*' if o2 == 'F2' else 'O2' if o2 == 'J' else 'O3')

        self.bland_altman_plot(cohort1, cohort2, title=_title, measurement='Curvature index',
                               units='$[dm^{-1}]$', xlimits=(-2.5, 1.0), ylimits=(-1, 1))
        # self.bland_altman_percentage_plot(cohort1, cohort2, title='Curvature % difference F1 vs ' + o2)

    def bland_altman_plot(self, data1, data2, title, measurement, units, xlimits, ylimits, *args, **kwargs):
        # print(data1)
        data1 = np.asarray(data1)
        data2 = np.asarray(data2)
        mean = np.mean([data1, data2], axis=0)
        diff = data1 - data2  # Difference between data1 and data2
        md = np.mean(diff)  # Mean of the difference
        sd = np.std(diff, axis=0)  # Standard deviation of the difference

        htn_bsh = np.zeros((10, 1), dtype=np.bool)
        htn_bsh[2] = 1
        htn_bsh[8] = 1
        htn_no_bsh = np.invert(htn_bsh)
        htn_mean = mean[10:]
        htn_diff = diff[10:]
        plt.figure(figsize=(4, 4))
        plt.scatter(np.extract(htn_no_bsh, htn_mean), np.extract(htn_no_bsh, htn_diff), marker='d', s=90)
        plt.scatter(np.extract(htn_bsh, htn_mean), np.extract(htn_bsh, htn_diff), marker='d', s=90)
        plt.scatter(mean[:10], diff[:10], *args, **kwargs, marker='d', s=90)
        plt.axhline(md, color='black', linestyle='--')
        plt.axhline(md + 1.96 * sd, color='gray', linestyle=':')
        plt.axhline(md - 1.96 * sd, color='gray', linestyle=':')

        # _, _, _, se = self.calculate_standard_error(mean)
        # ci_loa_height = sd * se
        # ci_loa_x = mean.min(), mean.max()

        # plt.errorbar(ci_loa_x, [md + 1.96 * sd] * 2,
        #              yerr=ci_loa_height, fmt='none',
        #              capsize=10, c='r')
        #
        # plt.errorbar(ci_loa_x, [md - 1.96 * sd] * 2,
        #              yerr=ci_loa_height, fmt='none',
        #              capsize=10, c='r')

        # plt.title(title)
        plt.xlabel(measurement + ', average value {}'.format(units), fontsize=12)
        plt.ylabel(measurement + ', difference {}'.format(units), fontsize=13)
        plt.xlim(xlimits)
        plt.ylim(ylimits)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_path, ' '.join([measurement, view, segment, 'F1_' + o2 + '.svg'])),
                    dpi=1200)
        plt.close()
        # plt.show()

    def bland_altman_percentage_plot(self, data1, data2, title, *args, **kwargs):
        data1 = np.round(np.asarray(data1), decimals=2)
        data2 = np.round(np.asarray(data2), decimals=2)

        mean = np.mean([data1, data2], axis=0)
        diff = data1 - data2  # Difference between data1 and data2
        diff_pr = diff / mean * 100
        md = np.mean(diff_pr)  # Mean of the difference
        sd = np.std(diff_pr, axis=0)  # Standard deviation of the difference

        plt.scatter(mean, diff_pr, *args, **kwargs)
        plt.axhline(md, color='gray', linestyle='--')
        plt.axhline(md + 1.96 * sd, color='gray', linestyle=':')
        plt.axhline(md - 1.96 * sd, color='gray', linestyle=':')

        _, _, _, se = self.calculate_standard_error(mean)
        ci_loa_height = sd * se
        ci_loa_x = mean.min(), mean.max()

        # plt.errorbar(ci_loa_x, [md + 1.96 * sd] * 2,
        #              yerr=ci_loa_height, fmt='none',
        #              capsize=10, c='r')
        #
        # plt.errorbar(ci_loa_x, [md - 1.96 * sd] * 2,
        #              yerr=ci_loa_height, fmt='none',
        #              capsize=10, c='r')
        plt.ylim((-1000, 1000))
        plt.title(title)
        plt.show()


if __name__ == '__main__':

    # VARIABILITY ANALYSIS
    #
    measurements_path = os.path.join('C:/', 'Data', 'ProjectCurvature', 'InterObserverStudy', 'StudyResults')
    output_path = os.path.join('C:/', 'Data', 'ProjectCurvature', 'InterObserverStudy', 'StudyResults')

    measurements_filename = 'InterObserverStudy.xlsx'

    var = VariabilityAnalysis(measurements_path, output_path, measurements_filename)
    # var._test_sem_calculations()
    # ranges = pd.DataFrame()
    for o2 in ['F2', 'M', 'J']:
        view = ''
        segment = ''
        df_range = var.calculate_sem_single_index(o2=o2)
        var.bland_altman_plot_single_index(o2=o2)
    #     ranges = pd.concat((ranges, df_range), axis=0)
    #     for view in ['PLAX', '4C']:
    #         var.bland_altman_plot_multi_index(o2=o2, view=view, segment='ratio')
    #         df_range = var.calculate_sem_multi_index(o2=o2, view=view, segment='ratio')
    #         ranges = pd.concat((ranges, df_range), axis=0)
    # ranges.to_csv(os.path.join(var.output_path, 'ranges.csv'))
    # print(ranges)
    # STRAIN ANALYSIS
    #
    patient_data_path = os.path.join('C:\Data\ProjectCurvature\Analysis\Output_HTN\Statistics')
    curvature_results = os.path.join('C:/', 'Data', 'ProjectCurvature', 'Analysis', 'Output')
    output = check_directory(os.path.join('C:\Data\ProjectCurvature\Analysis\Output_HTN\Statistics\plots', 'EDA'))
    # measurements = 'AduHeart_Measurements.xlsx'
    # twodstrain = 'AduHeart_Strain_MW.xlsx'
    # curvature = 'master_table_full.csv'
    # patient_info = 'AduHeart_PatientData_Full.xlsx'
    merged_data = 'Measurements_and_2DstrainPlotting.csv'
    #
    # anal = StrainAnalysis(patient_data_path, curvature_results, output, merged_data_filename=merged_data)

    # anal.plots_wt_and_curvature_vs_markers(True)
    # anal.plot_curv_vs_wt(True)
    # anal.get_statistics()
    # anal.linear_regression_basic_factors(False, show_plots=True)

    # STATANALYSIS

    source = os.path.join('C:\Data\ProjectCurvature\Analysis\Output_HTN\Statistics')
    # datafile = 'Measurements_and_2DstrainPlottingAll.csv'
    datafile = 'Measurements_and_2DstrainPlotting.csv'


    output = os.path.join(source, r'plots\EDA')
    #
    # anal = StatAnalysis(input_path=source, output_path=output, data_filename=datafile)
    # anal.read_dataframe('patient_ID')

    # Analysis
    # anal.plot_histograms(covariates=('Average septal curvature [cm-1]',
    #                                  r'Wall thickness ratio in 4CH view',
    #                                  r'Wall thickness ratio in PLAX view'))
    # anal.plot_relations(pairs=((r'Wall thickness ratio in PLAX view', r'Average septal curvature [cm-1]'),
    # (r'Wall thickness ratio in 4CH view', r'Average septal curvature [cm-1]')))
    # anal.perform_analysis(covariates=('Average septal curvature [cm-1]', r'Wall thickness ratio in 4CH view',
    #                                  r'Wall thickness ratio in PLAX view'))
    # anal.plot_boxplots(covariates=('Average septal curvature [cm-1]',
    #                                  r'Wall thickness ratio in 4CH view',
    #                                  r'Wall thickness ratio in PLAX view',
    #                                  r'strain_avc_Basal Septal'), hue='SB')
    # # anal.predict_with_lr()

    # Preprocessing
    # group_anal = anal.get_df_pre_processing(print=True)
    # group_anal.to_csv(os.path.join(output, 'analysis', 'biomarkers_proper_scale.csv'))
    # strain_anal = StrainAnalysis(patient_data_path=source, output_path=output,
    #                              curvature_results_path=source, merged_data_filename=datafile)
    # strain_anal.plot_curv_vs_wt(save_figures=True)
    # strain_anal.linear_regression_basic_factors(to_file=True, show_plots=True)
