import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib import cm
import matplotlib as mpl
import matplotlib.patheffects as pef
import seaborn as sns
from scipy.signal import savgol_filter


class PlottingCurvature:
    # -----VentricleVisualization---------------------------------------------------------------------------------------

    def __init__(self, source='/home/mat/Python/data/echo_delineation', output_path='', ventricle=None):

        self.source = source
        self.output_path = output_path
        self.data = ventricle.data
        self.id = ventricle.id
        self.number_of_frames = ventricle.number_of_frames
        self.curvature = ventricle.ventricle_curvature
        self.c_normalized = ventricle.vc_normalized
        self.es_frame, self.ed_frame = ventricle.es_frame, ventricle.ed_frame
        self.mean_curvature = ventricle.get_mean_curvature_over_time()

        self.mc_normalized = ventricle.get_normalized_curvature(self.mean_curvature)
        self.es_apex = self.data[self.es_frame, ventricle.apex*2:ventricle.apex*2+2]
        self.ed_apex = self.data[self.ed_frame, ventricle.apex*2:ventricle.apex*2+2]
        self.ed_apex_id = ventricle.apex

    def _get_translated_element(self, _frame_number, _ref=()):

        if not np.any(_ref):
            x_ref = np.mean(self.data[_frame_number, ::2])
            y_ref = np.mean(self.data[_frame_number, 1::2])
        else:
            x_ref = _ref[0]
            y_ref = _ref[1]
        x_centered = self.data[_frame_number, ::2] - x_ref
        y_centered = self.data[_frame_number, 1::2] - y_ref

        return x_centered, y_centered, (x_ref, y_ref)

    @staticmethod
    def _append_missing_curvature_values(curve):
        # return np.concatenate([[curve[0]], curve, [curve[-1]]])  # not necessary with gradient curvature
        return curve

    def plot_single_frame(self, frame_number=0):

        xx, yy, _ = self._get_translated_element(frame_number)

        fig, ax0 = plt.subplots(figsize=(5, 8))
        ax0.plot(xx, yy, 'gd-', ms=5)
        ax0.set_title('Case {}, frame number: {}'.format(self.id, frame_number))
        ax0.set_xlim(-40, 45)
        ax0.set_ylim(-45, 55)
        fig.tight_layout()
        fig.savefig(fname=os.path.join(self.output_path, '{}_frame_{}'.format(self.id, frame_number)))
        fig.close()

    def plot_single_frame_with_curvature(self, frame_number=0):

        xx, yy, _ = self._get_translated_element(frame_number)
        curv = self._append_missing_curvature_values(self.c_normalized[frame_number])

        fig, (ax0, ax1) = plt.subplots(1, 2, gridspec_kw={'width_ratios': [3, 5]}, figsize=(13, 8))

        ax0.plot(xx, yy, 'gd-', ms=5)
        ax0.set_title('Case {}, frame number: {}'.format(self.id, frame_number))
        ax0.set_xlim(-40, 45)
        ax0.set_ylim(-45, 55)

        ax1.plot(curv)
        ax1.set_title('Geometric point-to-point curvature')
        ax1.axhline(y=0, color='r', linestyle='--')

        fig.tight_layout()
        fig.savefig(fname=os.path.join(self.output_path, '{}_frame_{}_with_curv'.format(self.id, frame_number)))
        fig.close()

    def plot_mean_curvature(self):

        fig, (ax0, ax1) = plt.subplots(1, 2, gridspec_kw={'width_ratios': [3, 5]}, figsize=(13, 8))

        ax0.set_title('LV trace, full cycle'.format(self.id))
        ax0.set_xlim(-30, 55)
        ax0.set_ylim(-85, 5)
        ax0.set_xlabel('Short axis')
        ax0.set_ylabel('Long axis')

        ax1.set_title('Mean geometric point-to-point curvature')
        ax1.axhline(y=0, c='k', ls='-.', lw=2)
        ax1.set_xlim(-1, len(self.mc_normalized) + 2)
        ax1.set_ylim(-0.07, 0.13)
        ax1.vlines(self.ed_apex_id + 1, 0, self.mean_curvature[self.ed_apex_id], color='k', linestyles='-.', lw=1)
        #  Added 1 to ed_apex_id because the plot is moved by one (due to lack of curvature at end points)
        ax1.set_xlabel('Point number')
        ax1.set_ylabel('Curvature $[m^{-1}]$')

        ext = 'curvature'

        legend_elements0 = \
            [Line2D([0], [0], c='w', marker='d', markerfacecolor='k', markersize=9, label='Apex at ED')]
        legend_elements1 = [Line2D([0], [0], c='b', lw=2, label='Negative curvature'),
                            Line2D([0], [0], c='r', lw=2, label='Positive curvature'),
                            Line2D([0], [0], c='k', ls='-.', label='Apical point')]

        for frame_number in range(self.number_of_frames):

            xx, yy, _ = self._get_translated_element(frame_number, self.ed_apex)
            yy *= -1
            norm_curv = self._append_missing_curvature_values(self.c_normalized[self.ed_frame])

            color_tr = cm.coolwarm(norm_curv)
            color_tr[:, -1] = 0.3
            color = cm.seismic(norm_curv)
            size = 10
            ax0.scatter(xx, yy, c=color, edgecolor=color_tr, marker='o', s=size)

        curv = self._append_missing_curvature_values(self.mean_curvature)
        points = np.array([np.linspace(0, len(curv) - 1, len(curv)), curv]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        norm = plt.Normalize(-0.125, 0.125)  # Arbitrary values, seem to correspond to the ventricle image

        # norm_curv = self._append_missing_curvature_values(self.mc_normalized)
        lc = LineCollection(segments, cmap='seismic', alpha=0.4, norm=norm)
        lc.set_array(curv)
        lc.set_linewidth(5)
        ax1.add_collection(lc)

        ax0.scatter(0, 0, c='k', marker='d', s=80, alpha=1, label='Apex at ED')
        ax0.legend(handles=legend_elements0, loc='upper left', title='Cardiac cycle')
        ax1.legend(handles=legend_elements1, loc='upper right', title='Curvature')
        fig.tight_layout()
        fig.savefig(fname=os.path.join(self.output_path, '{}_mean_colour_by_{}'.format(self.id, ext)))
        plt.close()

    def plot_all_frames(self, coloring_scheme=None):
        fig, (ax0, ax1) = plt.subplots(1, 2, gridspec_kw={'width_ratios': [3, 5]}, figsize=(14, 6))

        ax0.set_title('LV trace, full cycle'.format(self.id))
        ax0.set_ylim(-10.1, 1.0)
        ax0.set_xlim(-5.0, 5.0)
        ax0.set_xlabel('Short axis $[cm]$')
        ax0.set_ylabel('Long axis $[cm]$')

        ax1.set_title('Geometric point-to-point curvature')
        # ax1.axhline(y=0, c='k', ls='-.', lw=1)
        ax1.axvline(x=00, c='k', ls='-.', lw=1)
        ax1.axvline(x=120, c='k', ls='-.', lw=1)
        ax1.set_ylim(-7, 4)
        ax1.set_xlim(-10, 140)

        # ax1.vlines(self.ed_apex_id+1, 0, max(self.curvature[:, self.ed_apex_id]), color='k', linestyles='-.', lw=1)
        #  Added 1 to ed_apex_id because the plot is moved by one (due to lack of curvature at end points)
        ax1.set_xlabel('Region of interest')
        ax1.set_ylabel('Curvature $[dm^{-1}]$')

        if coloring_scheme == 'curvature':
            xx, yy, _ = self._get_translated_element(self.ed_frame, self.ed_apex)
            yy *= -1
            curv = self._append_missing_curvature_values(self.curvature[self.ed_frame])
            # ax0.plot(xx, yy, 'k--', lw=3)
            # ax1.plot(curv, '--', c='black', lw=2)

            xx, yy, _ = self._get_translated_element(self.es_frame, self.ed_apex)
            yy *= -1
            curv = self._append_missing_curvature_values(self.curvature[self.es_frame])
            # ax0.plot(xx, yy, 'k:', lw=3)
            ax1.plot(curv, ':', c='black', lw=2, alpha=0)

            legend_elements0 = \
                [Line2D([0], [0], c='k', ls='--', lw=2, label='End diastole'),
                 Line2D([0], [0], c='k', ls=':', lw=2, label='End systole')]
            legend_elements1 = [Line2D([0], [0], c='k', ls='--', lw=2, label='End diastole'),
                                Line2D([0], [0], c='k', ls=':', lw=2, label='End systole'),
                                Line2D([0], [0], c='b', lw=2, label='Negative curvature'),
                                Line2D([0], [0], c='r', lw=2, label='Positive curvature')]
        else:
            legend_elements0 = \
                [Line2D([0], [0], c='b', lw=2, label='Beginnning (end diastole)'),
                 Line2D([0], [0], c='purple', lw=2, label='Contraction'),
                 Line2D([0], [0], c='r', lw=2, label='End systole'),
                 Line2D([0], [0], c='g', lw=2, label='Towrds end diastole'),
                 Line2D([0], [0], c='w', marker='d', markerfacecolor='k', markersize=9, label='Apical point')]
            legend_elements1 = [Line2D([0], [0], c='b', lw=2, label='Beginnning'),
                                Line2D([0], [0], c='purple', lw=2, label='Contraction'),
                                Line2D([0], [0], c='r', lw=2, label='End systole'),
                                Line2D([0], [0], c='g', lw=2, label='End'),
                                Line2D([0], [0], c='k', ls=':', label='Apical point')]

        for frame_number in range(self.number_of_frames):
            frame_number = self.ed_frame
            xx, yy, _ = self._get_translated_element(frame_number, self.ed_apex)
            yy *= -1
            curv = self._append_missing_curvature_values(self.curvature[frame_number])[:130]
            norm_curv = self._append_missing_curvature_values(self.c_normalized[self.ed_frame])
            if coloring_scheme == 'curvature':
                color_tr = cm.seismic(norm_curv)
                color_tr[:, -1] = 0.9
                color = cm.seismic(norm_curv)
                # color[:, -1] = 0.01
                size = 10
                ax0.plot(xx, yy, c='gray', lw=2, alpha=0.005)
                ax0.scatter(xx, yy, c=color_tr, edgecolor=color, marker='o', s=size, alpha=0.1)

                points = np.array([np.linspace(0, len(curv)-1, len(curv)), curv]).T.reshape(-1, 1, 2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)
                norm = plt.Normalize(-15, 15)  # Arbitrary values, seem to correspond to the ventricle image
                lc = LineCollection(segments, cmap='seismic', alpha=1, norm=norm)
                lc2 = LineCollection(segments, color='gray', alpha=0.2, norm=norm)
                lc.set_array(curv)
                lc.set_linewidth(2)
                lc.set_edgecolor('k')
                ax1.add_collection(lc)
                ax1.add_collection(lc2)
                ext = 'curvature'
                # break
            else:
                color_tr = np.array(cm.brg(frame_number/self.number_of_frames)).reshape((1, -1))[0]
                color_tr[-1] = 0.2
                ax0.plot(xx, yy, c=color_tr, marker='.')
                ax1.plot(curv, c=color_tr, lw=2)
                ext = 'frame'

        # ax0.scatter(0, 0, c='k', marker='d', s=80, alpha=1, label='Apex at ED')
        ax0.legend(handles=legend_elements0, loc='lower left', title='Cardiac cycle')
        # ax1.legend(handles=legend_elements1, loc='upper right', title='Curvature')
        ax1.set_xticks(ticks=[0, 40, 80, 120])
        ax1.tick_params(axis='x', which='both',      # both major and minor ticks are affected
        bottom=False,      # ticks along the bottom edge are off
        top=False,         # ticks along the top edge are off
        labelbottom=False) # labels along the bottom edge are off

        norm = mpl.colors.Normalize(vmin=-2, vmax=2)
        cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.seismic)
        cmap.set_array([norm])
        fig.colorbar(cmap)
        fig.suptitle('Geometric curvature in the trace of LV')
        # fig.tight_layout()
        if '.' in self.id:
            self.id = self.id.replace('.', '_')
        print(os.path.join(self.output_path, '{}_colour_by_{}.png'.format(self.id, ext)))
        fig.savefig(fname=os.path.join(self.output_path, '{}_colour_by_{}.png'.format(self.id, ext)))
        plt.clf()
        plt.close()

    def plot_heatmap(self, smooth=False):
        if smooth:
            for point in range(self.curvature.shape[1]):
                self.curvature[:, point] = savgol_filter(self.curvature[:, point],
                                                         7, polyorder=5, mode='interp')
        print(self.curvature.shape)
        print(self.ed_frame)

        fig = sns.heatmap(self.curvature.T, vmax=2, vmin=-2, center=0, cmap='seismic')
        fig.set_title('Curvature heatmap')
        apex_pos = int(self.curvature.shape[1] / 2)
        b_al_pos = self.curvature.shape[1] - 1
        plt.yticks([1, apex_pos, b_al_pos], ['Basal\ninferoseptal', 'Apical', 'Basal\nanterolateral'],
                   rotation='horizontal')
        plt.xticks([int(self.curvature.shape[0] / 2)], ['Time'], rotation='horizontal')

        plt.tick_params(axis=u'both', which=u'both', length=0)
        # plt.axhline(y=20,  c='k', ls='-.', lw=1)
        # plt.axhline(y=149, c='k', ls='-.', lw=1)
        plt.axvline(x=11, c='w', ls=':', lw=2, path_effects=[pef.Stroke(linewidth=3, foreground='k'), pef.Normal()])
        plt.axvline(x=13, c='w', ls=':', lw=2, path_effects=[pef.Stroke(linewidth=3, foreground='k'), pef.Normal()])
        plt.annotate(xy=(12, 200), xytext=(17, 250), s='End-diastole', color='w', fontsize=14,fontstyle='oblique',
                     path_effects=[pef.Stroke(linewidth=2, foreground='k'), pef.Normal()],
                     arrowprops={'arrowstyle': mpl.patches.ArrowStyle("->"), 'color': 'w',
                                 'path_effects': [pef.Stroke(linewidth=3, foreground='k'), pef.Normal()], 'lw': 2})
        plt.annotate(xy=(15, 85), xytext=(20, 90), s='Region of interest', color='w', fontsize=14, fontstyle='oblique',
                     path_effects=[pef.Stroke(linewidth=2, foreground='k'), pef.Normal()],
                     arrowprops={'arrowstyle': mpl.patches.ArrowStyle("-[", widthB=2.4, lengthB=0.4), 'color': 'w',
                    'path_effects': [pef.Stroke(linewidth=3, foreground='k'), pef.Normal()], 'lw': 2})
        plt.tight_layout()
        plt.savefig(fname=os.path.join(self.output_path, 'Heatmap of {}.png'.format(self.id)))
        plt.close()

# -----END-VentricleVisualization-----------------------------------------------------------------------------


class PlottingDistributions:
    # -----DistributionVisualization--------------------------------------------------------------------------

    def __init__(self, df, series, output_path):
        self.df = df
        self.series = series
        self.output_path = output_path

    def _save_plot(self, plot_name, plot_data):
        plot_data.savefig(os.path.join(self.output_path, plot_name))
        plt.close()

    def set_series(self, series):
        self.series = series

    def plot_distribution(self, show=False):

        f, axes = plt.subplots(1, 2, figsize=(10, 6))
        sns.despine(left=True)
        sns.kdeplot(self.df[self.series], shade=True, color='b', ax=axes[0], label='PDF of \' ' + self.series + '\'')
        sns.distplot(self.df[self.series], kde=False, rug=True, color='r', bins=None, ax=axes[1])

        series_max = max(self.df[self.series])
        xlim = (min(self.df[self.series]) - 0.1 * series_max, series_max + 0.1 * series_max)

        for i in range(2):
            axes[i].set_xlim(xlim)

        axes[0].set_title('Kernel density distribution of \'' + self.series + '\' index')
        axes[1].set_title('Histogram of \'' + self.series + '\' index')
        axes[1].set_xlabel('Value of \'' + self.series + '\'')
        axes[1].set_ylabel('Count')
        sns.set()
        plt.tight_layout()

        if show:
            plt.show()
        self._save_plot(self.series + '.svg', f)
        plt.close()

    def plot_multiple_distributions(self, group_by, show=False):

        unique_labels = np.sort(self.df[group_by].unique())
        plot_name = 'distribution_' + self.series + '_by_' + group_by
        _ = plt.figure(figsize=(15, 8))
        for label in unique_labels:
            group = self.df[self.df[group_by] == label]
            _ = sns.distplot(group[self.series], label=str(label), hist=False, rug=True)

        _ = plt.gcf()

        if show:
            plt.show()
        self._save_plot(plot_name + '.svg', _)

    def plot_multiple_boxplots(self, group_by, hue=None, show=False):

        _ = plt.figure(figsize=(7.5, 2))  # with controls: 7, 3
        _ = sns.boxplot(x=self.series, y=group_by, hue=hue, data=self.df, orient='h')
        _ = plt.gcf()

        if show:
            plt.show()
        plot_name = 'boxplot_' + self.series + '_by_' + group_by

        plt.xlabel(self.series, fontsize=23)
        plt.xticks(fontsize=17)
        plt.ylabel('')
        plt.ylim(1.6, -0.6) # change to 2.6 for 3 groups
        plt.yticks([0, 1], ['', ''])

        if 'Average septal curvature [cm-1]' in self.series:
            plt.xlabel('Average septal curvature $[dm^{-1}]$', fontsize=23)

        # if 'SB' in group_by and len(group_by) == 2:
        #     plt.yticks([0, 1, 2], ['HTN w/BSH', 'HTN no BSH', 'Controls'], fontsize=16)

        if 'strain_avc_Basal' in self.series:
            plt.xlabel('Basal septal strain [%]')
            plt.xticks([-8, -12, -16, -20, -24])
        if 'Wall thickness' in self.series:
            plt.xlim((0.7, 2.2))

        if '85 percentile' in group_by:
            plt.yticks([0, 1, 2], ['HTN {$P^{ASC}_{>15}$}', 'HTN {$P^{ASC}_{<15}$}', 'Controls'], fontsize=18)
        elif 'SB' in group_by:
            # plt.yticks([1, 0, 2], ['HTN w/BSH', 'HTN no BSH', 'Controls'], fontsize=16)  # with controls
            plt.yticks([0, 1], ['HTN no BSH', 'HTN w/BSH'], fontsize=16)

        if hue is not None:
            plot_name += '_on_' + hue
        plt.tight_layout()
        self._save_plot(plot_name + '.svg', _)

    def plot_2_distributions(self, series1, series2, kind, show=False):

        g = sns.jointplot(series1, series2, data=self.df, kind=kind,
                          color='g', height=6, space=0)
        g.plot_joint(plt.scatter, c="grey", s=20, linewidth=1, marker="+")
        g.ax_joint.collections[0].set_alpha(0)
        g.fig.suptitle('Bi-variate distribution')
        sns.set()
        plt.tight_layout()

        if show:
            plt.show()
        self._save_plot(series1 + '_vs_' + series2 + '_' + kind + '.png', g)

    def plot_with_labels(self, series1, series2, w_labels=True, show=False):

        if w_labels:
            lm = sns.lmplot(x=series1, y=series2, data=self.df, palette='black',
                            markers=['o']).fig
        else:
            lm = sns.lmplot(x=series1, y=series2, data=self.df, hue='dummy',
                            robust=False, ci=99, legend=False, height=6.5, aspect=1.3,
                            scatter_kws={"s": 100, 'color': 'k'}, line_kws={'linewidth': 4, 'color': 'firebrick'})

        # lm = plt.gcf()
        # lm.suptitle('Relation between curvature index and wall thickness ratio')
        plt.xlabel(series1, fontsize=27)
        if 'Average septal curvature' in series1:
            plt.xlabel(r'Average septal curvature $[dm^{-1}]$', fontsize=27)
        if 'Average septal curvature [cm-1]' in series2:
            plt.ylabel(r'Average septal curvature $[dm^{-1}]$', fontsize=27)
        if 'strain_avc_Basal' in series2:
            plt.ylabel('Basal septal strain [%]', fontsize=30)
        if 'Wall thickness' in series1:
            plt.xlim(0.7, 2.2)
            plt.ylabel('')

        plt.ylim((-24, -6))
        plt.xticks(fontsize=19)
        plt.yticks(fontsize=19)

        # sns.set()
        plt.tight_layout()

        if show:
            plt.show()
        self._save_plot(series1.replace('/', '_') + '_vs_' + series2 + '_labeled.svg', lm)
        plt.clf()
        plt.close()


if __name__ == '__main__':
    pass
