from tethys_sdk.gizmos import DatePicker, MapView, MVLayer, MVView, TextInput, Button, ButtonGroup, LinePlot, \
    ScatterPlot, ToggleSwitch, RangeSlider, TimeSeries, SelectInput, TableView, BarPlot
    # PlotView is deprecated as of Tethys 1.2
    # PlotView

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .model import recessionExtract, createAbJson, createStatsInfo, getSite
import pandas as pd
import numpy as np
from .app import RecessionAnalyzer
import os
import cPickle as pickle
import simplejson as json
from datetime import datetime
import requests
# import zipfile2 as zipfile
import zipfile

import urllib
import io

@login_required()
def home(request):
    """
    Controller for the app home page.
    """
    print 'start'
    print datetime.now().time()
    gages_initial = []
    start_initial = '2018-1-30'
    stop_initial = '2018-2-2'

    timeseries_plot = []
    scatter_array = []
    scatter_plot_view = []
    gage_names = []
    select_gage_options_tuple = []

    # This is new
    temp_dir = RecessionAnalyzer.get_app_workspace().path
    res_ids = request.GET.getlist('WofUri')
    # res_ids = []
    # res_ids.append('cuahsi-wdc-2017-04-03-30616779')
    # res_ids.append('cuahsi-wdc-2017-04-03-30650403')
    # res_ids.append('cuahsi-wdc-2017-04-03-30705857')
    print 'getting cuahsi ids'
    print datetime.now().time()
    for res_id in res_ids:
        # Check domain of host. This code assumes app will be hosted on a hydroshare server
        app_host = request.META['HTTP_HOST']
        if 'appsdev.hydroshare' in app_host:
            url_zip = 'http://qa-hiswebclient.azurewebsites.net/CUAHSI/HydroClient/WaterOneFlowArchive/' \
                      + res_id + '/zip'
        else:
            url_zip = 'http://data.cuahsi.org/CUAHSI/HydroClient/WaterOneFlowArchive/' \
                      + res_id + '/zip'

        r = requests.get(url_zip, verify=False)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        file_list = z.namelist()
        # Create id directory if it does not exist
        if not os.path.exists(temp_dir+'/id'):
            os.makedirs(temp_dir+'/id')
        for file in file_list:
            file_data = z.read(file)
            file_path = temp_dir + '/id/' + res_id + '.xml'
            with open(file_path, 'wb') as f:
                f.write(file_data)

        gage_name = getSite(res_id)
        gage_names.append(gage_name)
        select_gage_options_tuple.append((gage_name, gage_name))
    # New stuff ends here

    print 'done cuahsi data'
    print datetime.now().time()
    concave_initial = False
    nonlinear_fitting_initial = False
    rec_sense_initial = 1
    min_length_initial = 4
    antecedent_moisture_initial = 1
    lag_start_initial = 0

    #select_gage_options_initial = ['11476500']
    select_gage_options_initial = gage_names
    #select_gage_options_tuple = [('11476500', '11476500'), ('11477000', '11477000')]
    #select_gage_options_tuple = [(getSite(res_id), getSite(res_id))]

    abJson = ''
    seriesDict = {}
    scatter_plot_view22 = []
    line_plot_view22 = []
    context = {}
    gage_json = ''
    ab_stats = buildStatTable({'stats': []})
    submitted = False

    print 'reading sites files'
    print datetime.now().time()
    sites = pd.read_csv(temp_dir+'/app_files/huc_18.tsv', sep='\t', header=30,
                        index_col=False, skiprows=[31])

    # sites = pd.read_csv('/usr/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/public/huc_18.tsv', sep='\t', header=30,
    #                     index_col=False, skiprows=[31])
    sites = sites[sites.site_tp_cd == 'ST']
    names = sites.station_nm

    values = [str(x) for x in list(sites.site_no)]
    text = [num + ' ' + name[0:20] for (num, name) in zip(values, names)]
    gages_options_options = zip(text, values)
    gages_options_options_dict = dict(zip(values, text))


    # "Analyze recessions" button has been pressed
    # this stores new set of analysis parameters
    # and performs recession analysis, stores data in dictionaries
    # creates a new dropdown box with user gages
    print 'done with stuff before post'
    print datetime.now().time()
    if request.POST and 'analyze' in request.POST:

        # PRESERVE THE PREVIOUS STATE #

        gages_initial = request.POST.getlist("gages_input")
        start_initial = request.POST['start_input']
        stop_initial = request.POST['stop_input']

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
        new_file_path = os.path.join(app_workspace.path, 'current_plot.txt')
        pickle.dump(request.POST, open(new_file_path[:-4] + '.p', 'w'))
        post = pickle.load(open(new_file_path[:-4] + '.p', 'r'))

        submitted = True

        gage_json = json.dumps(gage_names)
        start = post['start_input']
        stop = post['stop_input']
        rec_sense = post['rec_sense_input']
        min_length = post['min_length_input']

        nonlin_fit = post.get('nonlinear_fitting_input', False)

        min_length = float(min_length)
        selectivity = float(rec_sense) * 500

        sitesDict, startStopDict = recessionExtract(gage_names, res_ids, start, stop,
                                                    ante=10, alph=0.90, window=3,
                                                    selectivity=selectivity,
                                                    minLen=min_length, option=1,
                                                    nonlin_fit=nonlin_fit)

        abJson, abDict = createAbJson(sitesDict, gage_names)

        a = []
        a0 = []
        b = []
        q = []
        g = []
        flow = np.array([])
        time = np.array([], dtype='<U10')
        gage_flow = []

        for gage in gage_names:
            a = a + abDict[gage]['a']
            a0 = a0 + abDict[gage]['a0']
            b = b + abDict[gage]['b']
            q = q + abDict[gage]['q']
            g = g + [str(gage)] * len(abDict[gage]['a'])

            flow2 = sitesDict[gage][gage].values
            flow = np.concatenate((flow, flow2), axis=0)
            time2 = sitesDict[gage].index.strftime('%Y-%m-%d')
            time = np.concatenate((time, time2), axis=0)
            gage_flow = gage_flow + [str(gage)] * len(sitesDict[gage][gage])

        dfinfo = np.array([g, a, a0, b, q])
        flow_info = np.array([gage_flow, time, flow])
        df = pd.DataFrame(data=np.transpose(dfinfo), columns=['Gage', 'a', 'a0', 'b', 'q'])
        flow_df = pd.DataFrame(data=np.transpose(flow_info), columns=['Gage', 'Time', 'Flow rate'])

        # new_file_path = "/usr/local/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/templates/recession_analyzer/flowdata.html"

        new_file_path = temp_dir+"/calculated_data/flowdata.html"
        flow_df.to_html(new_file_path)
        # newline = '{% extends "recession_analyzer/base.html" %}\n{% load tethys_gizmos %}\n{% block app_content %}'
        # line_prepender(new_file_path, newline)
        # newline = '{% endblock %}'
        # line_appender(new_file_path, newline)

        # new_file_path = "/usr/local/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/templates/recession_analyzer/dataframe.html"

        new_file_path = temp_dir+"/calculated_data/dataframe.html"
        df.to_html(new_file_path)
        # newline = '{% extends "recession_analyzer/base.html" %}\n{% load tethys_gizmos %}\n{% block app_content %}'
        # line_prepender(new_file_path, newline)
        # newline = '{% endblock %}'
        # line_appender(new_file_path, newline)

        # FIXME: Throw error here if len(gage_names) == 0

        for gage in gage_names:
            ts = sitesDict[gage]
            startStop = startStopDict[gage]
            startVec = startStop[0]
            endVec = startStop[1]
            flow = ts[gage]
            tsinds = ts.index

            series = []
            series.append({'name': 'Series',
                           'data': zip(flow[tsinds[0]:startVec[0]].index, flow[tsinds[0]:startVec[0]])})
            series.append({'name': ' Series',
                           'data': zip(flow[startVec[0]:endVec[0]].index, flow[startVec[0]:endVec[0]])})
            for i in np.arange(0, len(startVec) - 1):
                series.append({'name': ' Series',
                               'data': zip(flow[endVec[i]:startVec[i + 1]].index, flow[endVec[i]:startVec[i + 1]])})
                series.append({'name': ' Series',
                               'data': zip(flow[startVec[i+1]:endVec[i+1]].index, flow[startVec[i+1]:endVec[i+1]])})

            series.append({'name': ' hello',
                           'data': zip(flow[endVec[-1]:tsinds[-1]].index, flow[endVec[-1]:tsinds[-1]])})

            seriesDict[gage] = series
            line_plot_view22.append(buildFlowTimeSeriesPlot(series=seriesDict[gage], name=gage))
            # line_plot_view=buildFlowTimeSeriesPlot(series=seriesDict[gage], name=gage)


            avals = ts['A0n'][ts['A0n'] > 0].values
            bvals = ts['Bn'][ts['Bn'] > 0].values
            # tuplelist = zip(avals, bvals)

            tuplelist=[list(a) for a in zip(avals,bvals)]
            scatter_plot_view22.append(buildRecParamPlot(tuplelist=tuplelist, name=gage))

            # scatter_plot_view22 = buildRecParamPlot(tuplelist=tuplelist, name=gage)


        stats_dict = createStatsInfo(abJson)
        ab_stats = buildStatTable(stats_dict)


    gages_options = SelectInput(display_text='Select gage(s)',
                                name='gages_input',
                                multiple=True,
                                options=gages_options_options,
                                initial=[gages_options_options_dict[init] for init in gages_initial])

    start_options = DatePicker(name='start_input',
                               display_text='Start date',
                               autoclose=True,
                               format='yyyy-m-d',
                               start_date='01/01/1910',
                               initial=start_initial)

    stop_options = DatePicker(name='stop_input',
                              display_text='Stop date',
                              autoclose=True,
                              format='yyyy-m-d',
                              start_date='01/01/1910',
                              initial=stop_initial)

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


    # It appears the gizmos need a non arrayed chart in order to load properly

    female_dataset = {
        'name': 'Female',
        'color': '#ff6600',
        'data': [
            [161.2, 51.6], [167.5, 59.0], [159.5, 49.2], [157.0, 63.0],

        ]
    }

    scatter_plot_view1 = ScatterPlot(
        width='500px',
        height='500px',
        engine='highcharts',
        title='Scatter Plot',
        subtitle='Scatter Plot',
        x_axis_title='Height',
        x_axis_units='cm',
        y_axis_title='Weight',
        y_axis_units='kg',

        series=[
            female_dataset
        ]
    )
    test_plot = scatter_plot_view1



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

                    'line_plot_view22': line_plot_view22,

                    'ab_stats': ab_stats,
                    'scatter_plot_view22': scatter_plot_view22,
                    'select_gage_options': select_gage_options,
                    'abJson': abJson,
                    'seriesDict': seriesDict,
                    'gages_options': gages_options,
                    'start_options': start_options,
                    'test_plot':test_plot,

                    'stop_options': stop_options})

    return render(request, 'recession_analyzer/home.html', context)


def line_prepender(filename, line):
    with open(filename, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(line.rstrip('\r\n') + '\n' + content)


def line_appender(filename, line):
    with open(filename, 'r+') as f:
        f.read()
        f.write('\n' + line.rstrip('\r\n') + '\n')


def buildFlowTimeSeriesPlot(series, name):
    # highcharts_object = {
    #     'chart': {
    #         'zoomType': 'x'
    #     },
    #     'title': {
    #         'text': 'Flow time series'
    #     },
    #     'subtitle': {
    #         'text': name
    #     },
    #     'legend': {
    #         'layout': 'vertical',
    #         'align': 'right',
    #         'verticalAlign': 'middle',
    #         'borderWidth': 0,
    #         'enabled': False
    #     },
    #     'xAxis': {
    #         'title': {
    #             'enabled': True,
    #             'text': 'time',
    #             'offset': 35
    #         },
    #         'type': 'datetime',
    #         'tickLength': 10
    #     },
    #     'yAxis': {
    #         'title': {
    #             'enabled': True,
    #             'text': 'Discharge [cfs]'
    #         }
    #     },
    #     'tooltip': {
    #         'pointFormat': '{point.y} cfs',
    #         'valueDecimals': 2,
    #         'xDateFormat': '%d %b %Y %H:%M'
    #     },
    #     'series': series
    # }
    #
    # return TimeSeries(highcharts_object=highcharts_object,
    #                 width='70%',
    #                 height='300px',
    #                 attributes='id=' + name)
    print series
    timeseries_plot1 = TimeSeries(
        # height='500px',
        # width='500px',
        engine='highcharts',
        title='Flow time series',
        subtitle=name,
        y_axis_title='Discharge',
        y_axis_units='cfs',
        series=series,
        attributes=name
    )


    return timeseries_plot1
    # highcharts_object=highcharts_object,
    #                   width='70%',
    #                   height='300px',
    #                   attributes='id=' + name)


def buildRecParamPlot(tuplelist, name):
    # scatter_highchart = {
    #     'chart': {
    #         'type': 'scatter',
    #         'zoomType': 'xy'
    #     },
    #     'title': {
    #         'text': 'Recession parameters'
    #     },
    #     'subtitle': {
    #         'text': name
    #     },
    #     'legend': {
    #         'layout': 'vertical',
    #         'align': 'right',
    #         'verticalAlign': 'middle',
    #         'borderWidth': 0,
    #         'enabled': False
    #     },
    #     'exporting': {
    #         'enabled': True
    #     },
    #     'tooltip': {
    #         'pointFormat': 'b={point.y:,.2f}, a={point.x:,.2f}'
    #     },
    #     'xAxis': {
    #         'title': {
    #             'enabled': True,
    #             'text': 'a',
    #             'offset': 35
    #         },
    #         'type': 'logarithmic',
    #         'tickLength': 10
    #     },
    #     'yAxis': {
    #         'title': {
    #             'enabled': True,
    #             'text': 'b'
    #         }
    #     },
    #     'series': [{'name': ' ', 'data': tuplelist}]
    # }
    #
    # return ScatterPlot(highcharts_object=scatter_highchart,
    #                 width='33%',
    #                 height='300px',
    #                 attributes='id=' + name)
    actual_data = {
        'name': 'data',
        'data':tuplelist
    }


    scatter_plot_view122 = ScatterPlot(
        # width='500px',
        # height='500px',
        engine='highcharts',
        title='Recession parameters',
        subtitle=name,
        x_axis_title='x-axis',
        y_axis_title='y-axis',
        attributes=name,

        series=[
            actual_data,

        ]
    )
    return scatter_plot_view122

    # print tuplelist
    # return ScatterPlot(
    #     series=[male_dataset],
    #     # series=[{'name': ' ', 'data': tuplelist}],
    #                    width='500px',
    #                    height='500px',
    #                    engine='highcharts',
    #                    title='Scatter Plot',
    #                    subtitle='Scatter Plot',
    #                    x_axis_title='Height',
    #                    x_axis_units='cm',
    #                    y_axis_title='Weight',
    #                    y_axis_units='kg',
    #                    )

    # return ScatterPlot(series=[{'name': ' ', 'data': [[2,3],[4,5]]}],
    #                    engine='highcharts',
    #                    title='Recession parameters',
    #                    width='33%',
    #                    height='300px',
    #                    x_axis_title='Fixing Scatter plot',
    #                    x_axis_units='m',
    #                    y_axis_title='test2',
    #                    y_axis_units='m'
    #                    )


def buildStatTable(stats_info):
    return TableView(hover=True,
                     column_names=('Gage', 'Parameter', '25th %', '50th %', '75th %'),
                     rows=stats_info['stats'],
                     bordered=True,
                     condensed=True)


def buildStatPlot(categories, series):
    stats_highchart = {
        'chart': {
            'inverted': True,
            'zoomType': 'xy'
        },
        'title': {
            'text': 'Boxplot'
        },
        'subtitle': {
            'text': 'a-b values'
        },
        'xAxis': {
            'reversed': False,
            'title': {
                'text': 'Value'
            },
            'type': 'logarithmic',
            'maxPadding': 0.1,
            'minPadding': 0.1
        },
        'yAxis': {
            'title': {
                'text': 'Gage Name'
            },
            'categories': categories,
            'lineWidth': 1,
            'gridLineWidth': 0
        },
        'tooltip': {
            'headerFormat': '<b>{series.name}</b><br/>',
            'pointFormat': '{point.x}'
        },
        'legend': {
            'enabled': False
        },
        'series': series
    }

    return BarPlot(highcharts_object=stats_highchart,
                    width='33%',
                    height='300px',
                    attributes='id=')


@login_required()
def dataframe(request):
    """
    Controller for dataframe page.
    """

    temp_dir = RecessionAnalyzer.get_app_workspace().path

    # new_file_path = "/usr/local/lib/tethys/src/tethys_apps/tethysapp/recession_analyzer/templates/recession_analyzer/dataframe.html"

    new_file_path = temp_dir + "/calculated_data/dataframe.html"


    with open(new_file_path, 'r') as f:
        data = f.read()
    context = {'data':data}
    return render(request, 'recession_analyzer/dataframe.html', context)


@login_required()
def flowdata(request):
    """
    Controller for dataframe page.
    """
    temp_dir = RecessionAnalyzer.get_app_workspace().path

    new_file_path = temp_dir + "/calculated_data/flowdata.html"

    with open(new_file_path, 'r') as f:
        data = f.read()
    context = {'data': data}
    return render(request, 'recession_analyzer/flowdata.html', context)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)
