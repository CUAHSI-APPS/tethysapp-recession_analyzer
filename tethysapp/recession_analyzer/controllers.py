from tethys_sdk.gizmos import DatePicker, MapView, MVLayer, MVView, TextInput, Button, ButtonGroup, LinePlot, \
    ScatterPlot, ToggleSwitch, RangeSlider, TimeSeries, PlotView, SelectInput, TableView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .model import recessionExtract, createAbJson, createStatsInfo
import pandas as pd
import numpy as np
from .app import RecessionAnalyzer
import os
import cPickle as pickle
import simplejson as json
from datetime import datetime

import urllib
from io import StringIO

@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    concave_initial = False
    nonlinear_fitting_initial = False
    rec_sense_initial = 1
    min_length_initial = 4
    antecedent_moisture_initial = 1
    lag_start_initial = 0
    select_gage_options_initial = ['11476500']
    select_gage_options_tuple = [('11476500', '11476500'), ('11477000', '11477000')]
    abJson = ''
    seriesDict = {}
    scatter_plot_view = []
    line_plot_view = []
    context = {}
    gage_json = ''
    ab_table = buildStatTable({'data': '', 'outliers': ''})

    submitted = False

    # "Analyze recessions" button has been pressed
    # this stores new set of analysis parameters
    # and performs recession analysis, stores data in dictionaries
    # creates a new dropdown box with user gages

    if request.POST and 'analyze' in request.POST:

        # PRESERVE THE PREVIOUS STATE #

        gages_initial = request.POST.getlist("gages_input")
          
        print('\n\n\n\n\n')
        print(gages_initial)
        print(type(gages_initial))
        
        if 'concave_input' in request.POST:
            concave_initial = True
        else:
            concave_initial = False
        
        if 'nonlinear_fitting_input' in request.POST:
            nonlinear_fitting_initial = True
        else:
            nonlinear_fitting_initial = False
        
        rec_sense_initial = request.POST['rec_sense_input']
        min_length_initial = request.POST['min_length_input']
        lag_start_initial = request.POST['lag_start_input']
        
        antecedent_moisture_initial = request.POST['antecedent_moisture_input']

        ########################################

        app_workspace = RecessionAnalyzer.get_user_workspace(request.user)
        new_file_path = os.path.join(app_workspace.path, 'current_series_dict.txt')
        with open(new_file_path, "w") as file:
            file.write(str(app_workspace))

        new_file_path = os.path.join(app_workspace.path, 'current_plot.txt')
        pickle.dump(request.POST, open(new_file_path[:-4] + '.p', 'w'))
        post = pickle.load(open(new_file_path[:-4] + '.p', 'r'))
        
        submitted = True
        gage_names = ['11476500', '11477000']
        gage_json = json.dumps(gage_names)
        start = '2000-01-01'
        stop = '2015-01-01'
        rec_sense = post['rec_sense_input']
        min_length = post['min_length_input']

        nonlin_fit = post.get('nonlinear_fitting_input', False)

        min_length = float(min_length)
        selectivity = float(rec_sense) * 500

        sitesDict, startStopDict = recessionExtract(gage_names, start, stop,
                                                    ante=10, alph=0.90, window=3,
                                                    selectivity=selectivity,
                                                    minLen=min_length, option=1,
                                                    nonlin_fit=nonlin_fit)

        abJson = createAbJson(sitesDict, gage_names)

        new_file_path = os.path.join(app_workspace.path, 'current_dict.p')
        pickle.dump(sitesDict, open(new_file_path, 'w'))

        new_file_path = os.path.join(app_workspace.path, 'current_startStop.p')
        pickle.dump(startStopDict, open(new_file_path, 'w'))

        # FIXME: Add error here if len(gage_names) == 0

        for gage in gage_names:
            ts = sitesDict[gage]
            startStop = startStopDict[gage]
            startVec = startStop[0]
            endVec = startStop[1]
            flow = ts[gage]
            tsinds = ts.index

            series = []
            series.append({'name': ' ', 'color': '#0066ff',
                           'data': zip(flow[tsinds[0]:startVec[0]].index, flow[tsinds[0]:startVec[0]])})
            series.append({'name': ' ', 'color': '#ff6600',
                           'data': zip(flow[startVec[0]:endVec[0]].index, flow[startVec[0]:endVec[0]])})
            for i in np.arange(0, len(startVec) - 1):
                series.append({'name': ' ', 'color': '#0066ff',
                               'data': zip(flow[endVec[i]:startVec[i + 1]].index, flow[endVec[i]:startVec[i + 1]])})
                series.append({'name': ' ', 'color': '#ff6600',
                               'data': zip(flow[startVec[i+1]:endVec[i+1]].index, flow[startVec[i+1]:endVec[i+1]])})

            series.append({'name': ' ', 'color': '#0066ff',
                           'data': zip(flow[endVec[-1]:tsinds[-1]].index, flow[endVec[-1]:tsinds[-1]])})

            seriesDict[gage] = series
            line_plot_view.append(buildFlowTimeSeriesPlot(series=seriesDict[gage], name=gage))

            avals = ts['A0n'][ts['A0n'] > 0].values
            bvals = ts['Bn'][ts['Bn'] > 0].values
            tuplelist = zip(avals, bvals)
            scatter_plot_view.append(buildRecParamPlot(tuplelist=tuplelist, name=gage))

        # seriesJson = json.dumps(seriesDict, cls=DateTimeEncoder)
        # new_file_path = os.path.join(app_workspace.path, 'current_json.txt')
        # with open(new_file_path, "w") as outfile:
        #     json.dump(seriesDict, outfile, indent=4, cls=DateTimeEncoder)

        stats_dict = createStatsInfo(abJson)
        ab_table = buildStatTable(stats_dict)

    concave_options = ToggleSwitch(name='concave_input', size='small',
                                   initial=concave_initial, display_text='Concave recessions')

    nonlinear_fitting_options = ToggleSwitch(name='nonlinear_fitting_input',
                                             display_text='Nonlinear fitting',
                                             size='small', initial=nonlinear_fitting_initial)

    min_length_options = RangeSlider(name='min_length_input', min=4, max=10,
                                     initial=min_length_initial, step=1,
                                     attributes={"onchange": "showValue(this.value,'min_length_initial');"})

    rec_sense_options = RangeSlider(name='rec_sense_input', min=0, max=1,
                                    initial=rec_sense_initial, step=0.01,
                                    attributes={"onchange": "showValue(this.value,'rec_sense_initial');"})

    antecedent_moisture_options = RangeSlider(name='antecedent_moisture_input',
                                              min=0, max=1, initial=antecedent_moisture_initial, step=0.01,
                                              attributes=
                                              {"onchange": "showValue(this.value,'antecedent_moisture_initial');"})

    lag_start_options = RangeSlider(name='lag_start_input', min=0, max=3,
                                    initial=lag_start_initial, step=1,
                                    attributes={"onchange": "showValue(this.value,'lag_start_initial');"})

    select_gage_options = SelectInput(display_text='Select gage',
                                      name='gage_input', multiple=False,
                                      initial=select_gage_options_initial,
                                      options=select_gage_options_tuple,
                                      attributes={"onchange": "updatePlots(this.value);"})

    context.update({'rec_sense_initial': rec_sense_initial,
                    'antecedent_moisture_initial': antecedent_moisture_initial,
                    'lag_start_initial': lag_start_initial,
                    'gage_json': gage_json,
                    'min_length_initial': min_length_initial,
                    'concave_options': concave_options,
                    'nonlinear_fitting_options': nonlinear_fitting_options,
                    'min_length_options': min_length_options,
                    'submitted': submitted,
                    'antecedent_moisture_options': antecedent_moisture_options,
                    'lag_start_options': lag_start_options,
                    'rec_sense_options': rec_sense_options,
                    'line_plot_view': line_plot_view,
                    'ab_table': ab_table,
                    'scatter_plot_view': scatter_plot_view,
                    'select_gage_options': select_gage_options,
                    'abJson': abJson,
                    'seriesDict': seriesDict})

    return render(request, 'recession_analyzer/home.html', context)


def buildFlowTimeSeriesPlot(series, name):
    highcharts_object = {
        'chart': {
            'zoomType': 'x'
        },
        'title': {
            'text': 'Flow time series'
        },
        'subtitle': {
            'text': name
        },
        'legend': {
            'layout': 'vertical',
            'align': 'right',
            'verticalAlign': 'middle',
            'borderWidth': 0,
            'enabled': False
        },
        'xAxis': {
            'title': {
                'enabled': True,
                'text': 'time',
                'offset': 35
            },
            'type': 'datetime',
            'tickLength': 10
        },
        'yAxis': {
            'title': {
                'enabled': True,
                'text': 'Discharge [cfs]'
            }
        },
        'tooltip': {
            'pointFormat': '{point.y} cfs',
            'valueDecimals': 2,
            'xDateFormat': '%d %b %Y %H:%M'
        },
        'series': series
    }

    return PlotView(highcharts_object=highcharts_object,
                    width='70%',
                    height='300px',
                    attributes='id=' + name)


def buildRecParamPlot(tuplelist, name):
    scatter_highchart = {
        'chart': {
            'type': 'scatter',
            'zoomType': 'xy'
        },
        'title': {
            'text': 'Recession parameters'
        },
        'subtitle': {
            'text': name
        },
        'legend': {
            'layout': 'vertical',
            'align': 'right',
            'verticalAlign': 'middle',
            'borderWidth': 0,
            'enabled': False
        },
        'exporting': {
            'enabled': True
        },
        'tooltip': {
            'pointFormat': 'b={point.y:,.2f}, a={point.x:,.2f}'
        },
        'xAxis': {
            'title': {
                'enabled': True,
                'text': 'a',
                'offset': 35
            },
            'type': 'logarithmic',
            'tickLength': 10
        },
        'yAxis': {
            'title': {
                'enabled': True,
                'text': 'b'
            }
        },
        'series': [{'name': ' ', 'data': tuplelist}]
    }

    return PlotView(highcharts_object=scatter_highchart,
                    width='33%',
                    height='300px',
                    attributes='id=' + name)

def buildStatTable(stats_info):
    return TableView(hover=True,
                     column_names=('Gage', 'Parameter', '25th', '50th', '75th'),
                     rows=stats_info['data'],
                     bordered=True,
                     condensed=True)

# def buildStatTable(stats_info):
#     stat_table = {
#         'chart': {
#             'type': 'boxplot',
#         },
#         'title': {
#             'text': 'AB Stats'
#         },
#
#         'legend': {
#             'enabled': False
#         },
#
#         'xAxis': {
#             'categories': stats_info['x_axis'],
#             'title': {
#                 'text': 'Experiment No.'
#             }
#         },
#
#         'yAxis': {
#             'title': {
#                 'text': 'Observations'
#             },
#         },
#
#         'series': [{
#             'name': 'Observations',
#             'data': [],
#             'type': 'boxplot',
#         }, {
#             'name': 'Outlier',
#             'color': 'gray',
#             'type': 'scatter',
#             #'data': stats_info['outliers'],
#             'data': [],
#             'marker': {
#                 'fillColor': 'white',
#                 'lineWidth': 1,
#                 'lineColor': 'gray'
#             }
#         }]
#     }
#
#     return PlotView(highcharts_object=stat_table,
#                     width='100%',
#                     height='300px',
#                     attributes='id=ab-boxplot')


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)
